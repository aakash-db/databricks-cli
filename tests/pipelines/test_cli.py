# Databricks CLI
# Copyright 2017 Databricks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"), except
# that the use of services to which certain application programming
# interfaces (each, an "API") connect requires that the user first obtain
# a license for the use of the APIs from Databricks, Inc. ("Databricks"),
# by creating an account at www.databricks.com and agreeing to either (a)
# the Community Edition Terms of Service, (b) the Databricks Terms of
# Service, or (c) another written agreement between Licensee and Databricks
# for the use of the APIs.
#
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint:disable=redefined-outer-name

import json

import mock
import pytest
from click import Context, Command
from click.testing import CliRunner
import requests

import databricks_cli.pipelines.cli as cli
from tests.utils import provide_conf

DEPLOY_SPEC_NO_ID = '{"name": "asdf"}'
DEPLOY_SPEC = '{"id": "123", "name": "asdf"}'
PIPELINE_ID = "123"


@pytest.fixture()
def pipelines_api_mock():
    with mock.patch('databricks_cli.pipelines.cli.PipelinesApi') as PipelinesApiMock:
        _pipelines_api_mock = mock.MagicMock()
        PipelinesApiMock.return_value = _pipelines_api_mock
        yield _pipelines_api_mock


@pytest.fixture()
def click_ctx():
    """
    A dummy Click context to allow testing of methods that raise exceptions. Fixes Click capturing
    actual exceptions and raising its own `RuntimeError: There is no active click context`.
    """
    return Context(Command('cmd'))


@provide_conf
def test_create_pipeline_spec_arg(pipelines_api_mock, tmpdir):
    pipelines_api_mock.create = mock.Mock(return_value={"pipeline_id": PIPELINE_ID})

    path = tmpdir.join('/spec.json').strpath
    with open(path, 'w') as f:
        f.write(DEPLOY_SPEC_NO_ID)

    runner = CliRunner()
    result = runner.invoke(cli.deploy_cli, [path])

    assert PIPELINE_ID in result.stdout


@provide_conf
def test_create_pipeline_spec_option(pipelines_api_mock, tmpdir):
    pipelines_api_mock.create = mock.Mock(return_value={"pipeline_id": PIPELINE_ID})

    path = tmpdir.join('/spec.json').strpath
    with open(path, 'w') as f:
        f.write(DEPLOY_SPEC_NO_ID)

    runner = CliRunner()
    result = runner.invoke(cli.deploy_cli, ['--spec', path])

    assert PIPELINE_ID in result.stdout


@provide_conf
def test_deploy_cli_spec_arg(pipelines_api_mock, tmpdir):
    path = tmpdir.join('/spec.json').strpath
    with open(path, 'w') as f:
        f.write(DEPLOY_SPEC)
    runner = CliRunner()
    runner.invoke(cli.deploy_cli, [path])
    assert pipelines_api_mock.deploy.call_args[0][0] == json.loads(DEPLOY_SPEC)


@provide_conf
def test_deploy_spec_option(pipelines_api_mock, tmpdir):
    path = tmpdir.join('/spec.json').strpath
    with open(path, 'w') as f:
        f.write(DEPLOY_SPEC)
    runner = CliRunner()
    runner.invoke(cli.deploy_cli, ['--spec', path])
    assert pipelines_api_mock.deploy.call_args[0][0] == json.loads(DEPLOY_SPEC)


@provide_conf
def test_deploy_cli_incorrect_parameters(pipelines_api_mock, tmpdir):
    path = tmpdir.join('/spec.json').strpath
    with open(path, 'w') as f:
        f.write(DEPLOY_SPEC)
    runner = CliRunner()
    result = runner.invoke(cli.deploy_cli, [path, '--spec', path])
    assert result.exit_code == 1
    assert pipelines_api_mock.deploy.call_count == 0
    result = runner.invoke(cli.deploy_cli, ['--spec', path, path])
    assert result.exit_code == 1
    assert pipelines_api_mock.deploy.call_count == 0


@provide_conf
def test_delete_cli_id(pipelines_api_mock):
    runner = CliRunner()
    runner.invoke(cli.delete_cli, ['--pipeline-id', PIPELINE_ID])
    assert pipelines_api_mock.delete.call_args[0][0] == PIPELINE_ID


@provide_conf
def test_delete_cli_correct_parameters(pipelines_api_mock):
    runner = CliRunner()
    result = runner.invoke(cli.delete_cli, ['--pipeline-id', PIPELINE_ID])
    assert result.exit_code == 0
    assert pipelines_api_mock.delete.call_count == 1


@provide_conf
def test_deploy_spec_pipeline_id_is_not_changed_if_provided_in_spec(tmpdir):
    path = tmpdir.join('/spec.json').strpath
    with open(path, 'w') as f:
        f.write(DEPLOY_SPEC)
    runner = CliRunner()
    result = runner.invoke(cli.deploy_cli, ['--spec', path])

    assert '123' in result.stdout


@provide_conf
def test_deploy_update_delete_cli_correct_spec_extensions(pipelines_api_mock, tmpdir):
    pipelines_api_mock.create = mock.Mock(return_value={"pipeline_id": PIPELINE_ID})

    runner = CliRunner()
    path_json = tmpdir.join('/spec.json').strpath
    with open(path_json, 'w') as f:
        f.write(DEPLOY_SPEC_NO_ID)
    result = runner.invoke(cli.deploy_cli, ['--spec', path_json])
    assert result.exit_code == 0
    assert pipelines_api_mock.create.call_count == 1

    result = runner.invoke(cli.deploy_cli, ['--spec', path_json, '--pipeline-id', PIPELINE_ID])
    assert result.exit_code == 0
    assert pipelines_api_mock.deploy.call_count == 1

    result = runner.invoke(cli.delete_cli, ['--pipeline-id', PIPELINE_ID])
    assert result.exit_code == 0
    assert pipelines_api_mock.delete.call_count == 1
    pipelines_api_mock.reset_mock()

    path_case_insensitive = tmpdir.join('/spec2.JsON').strpath
    with open(path_case_insensitive, 'w') as f:
        f.write(DEPLOY_SPEC_NO_ID)
    result = runner.invoke(cli.deploy_cli, ['--spec', path_case_insensitive])
    assert result.exit_code == 0
    assert pipelines_api_mock.create.call_count == 1

    result = runner.invoke(cli.deploy_cli, [
        '--spec', path_case_insensitive,
        '--pipeline-id', PIPELINE_ID
    ])
    assert result.exit_code == 0
    assert pipelines_api_mock.deploy.call_count == 1

    result = runner.invoke(cli.delete_cli, ['--pipeline-id', PIPELINE_ID])
    assert result.exit_code == 0
    assert pipelines_api_mock.delete.call_count == 1
    pipelines_api_mock.reset_mock()


@provide_conf
def test_cli_id(pipelines_api_mock):
    for command in [cli.reset_cli, cli.stop_cli, cli.run_cli]:
        runner = CliRunner()
        runner.invoke(command, ['--pipeline-id', PIPELINE_ID])
        assert pipelines_api_mock.reset.call_args[0][0] == PIPELINE_ID


@provide_conf
def test_cli_no_id(pipelines_api_mock):
    for command in [cli.reset_cli, cli.stop_cli, cli.run_cli]:
        runner = CliRunner()
        result = runner.invoke(command, [])
        assert result.exit_code == 1
        assert pipelines_api_mock.reset.call_count == 0


@provide_conf
def test_get_cli_id(pipelines_api_mock):
    runner = CliRunner()
    runner.invoke(cli.get_cli, ['--pipeline-id', PIPELINE_ID])
    assert pipelines_api_mock.get.call_args[0][0] == PIPELINE_ID


@provide_conf
def test_get_cli_no_id(pipelines_api_mock):
    runner = CliRunner()
    result = runner.invoke(cli.get_cli, [])
    assert result.exit_code == 1
    assert pipelines_api_mock.get.call_count == 0


def test_validate_pipeline_id(click_ctx):
    empty_pipeline_id = ''
    pipeline_id_with_unicode = b'pipeline_id-\xe2\x9d\x8c-123'.decode('utf-8')
    invalid_pipline_ids = ['pipeline_id-?-123', 'pipeline_id-\\-\'-123', 'pipeline_id-/-123',
                           pipeline_id_with_unicode, empty_pipeline_id]
    with click_ctx:
        for pipline_id in invalid_pipline_ids:
            with pytest.raises(SystemExit):
                cli._validate_pipeline_id(pipline_id)
    assert cli._validate_pipeline_id('pipeline_id-ac345cd1') is None


@provide_conf
def test_duplicate_name_check_error(pipelines_api_mock, tmpdir):
    mock_response = mock.MagicMock()
    mock_response.text = '{"error_code": "RESOURCE_CONFLICT"}'
    pipelines_api_mock.create = mock.Mock(
        side_effect=requests.exceptions.HTTPError(response=mock_response))
    pipelines_api_mock.deploy = mock.Mock(
        side_effect=requests.exceptions.HTTPError(response=mock_response))

    path = tmpdir.join('/spec.json').strpath
    with open(path, 'w') as f:
        f.write(DEPLOY_SPEC_NO_ID)

    runner = CliRunner()
    result = runner.invoke(cli.deploy_cli, [path])
    assert pipelines_api_mock.create.call_count == 1
    assert result.exit_code == 1
    assert "already exists" in result.stdout

    with open(path, 'w') as f:
        f.write(DEPLOY_SPEC)
    result = runner.invoke(cli.deploy_cli, [path])
    assert result.exit_code == 1
    assert pipelines_api_mock.deploy.call_count == 1
    assert "already exists" in result.stdout


@provide_conf
def test_allow_duplicate_names_flag(pipelines_api_mock, tmpdir):
    path = tmpdir.join('/spec.json').strpath
    with open(path, 'w') as f:
        f.write(DEPLOY_SPEC_NO_ID)
    runner = CliRunner()
    runner.invoke(cli.deploy_cli, [path])
    assert pipelines_api_mock.create.call_args_list[0][0][1] is False

    runner.invoke(cli.deploy_cli, [path, "--allow-duplicate-names"])
    assert pipelines_api_mock.create.call_args_list[1][0][1] is True

    with open(path, 'w') as f:
        f.write(DEPLOY_SPEC)

    runner.invoke(cli.deploy_cli, [path])
    assert pipelines_api_mock.deploy.call_args_list[0][0][1] is False

    runner.invoke(cli.deploy_cli, [path, "--allow-duplicate-names"])
    assert pipelines_api_mock.deploy.call_args_list[1][0][1] is True


@provide_conf
def test_create_pipeline_no_update_spec(pipelines_api_mock, tmpdir):
    pipelines_api_mock.create = mock.Mock(return_value={"pipeline_id": PIPELINE_ID})

    path = tmpdir.join('/spec.json').strpath
    with open(path, 'w') as f:
        f.write(DEPLOY_SPEC_NO_ID)

    runner = CliRunner()
    result = runner.invoke(cli.deploy_cli, [path])

    assert result.exit_code == 0
    assert pipelines_api_mock.create.call_count == 1

    with open(path, 'r') as f:
        spec = json.loads(f.read())
    assert 'id' not in spec


@provide_conf
def test_deploy_pipeline_conflicting_ids(pipelines_api_mock, tmpdir):
    pipelines_api_mock.deploy = mock.Mock()

    path = tmpdir.join('/spec.json').strpath
    with open(path, 'w') as f:
        f.write(DEPLOY_SPEC)

    result = CliRunner().invoke(cli.deploy_cli, ['--spec', path, '--pipeline-id', "fake"])
    assert result.exit_code == 1
    assert pipelines_api_mock.deploy.call_count == 0


@provide_conf
def test_list_cli(pipelines_api_mock):
    pipelines_api_mock.list = mock.Mock()
    pipelines_api_mock.list.side_effect = [
        {'statuses': [{'pipeline_id': '1', 'state': 'RUNNING',
                       'cluster_id': '1024-161828-gram477', 'name': 'windfarm-pipe-v2', 'health': 'HEALTHY'},
                      {'pipeline_id': '2', 'state': 'RUNNING',
                       'cluster_id': '1024-160918-tees475', 'name': 'Wiki Pipeline', 'health': 'HEALTHY'}],
         'pagination': {
             'next_page_token': 'page2'}},
        {'statuses': [{'pipeline_id': '3', 'state': 'RUNNING',
                       'cluster_id': '1026-062128-blare168', 'name': 'airline-demo-workflow', 'health': 'HEALTHY'},
                      {'pipeline_id': '4', 'state': 'RUNNING',
                       'cluster_id': '1023-093505-corm4', 'name': 'Jira Automation Staging', 'health': 'HEALTHY'}],
         'pagination': {
             'next_page_token': 'page3',
             'prev_page_token': 'page2'}},
        {'statuses': [{'pipeline_id': '5', 'state': 'FAILED',
                       'cluster_id': '1023-090246-helix16', 'name': 'Marek', 'health': 'UNHEALTHY'},
                      {'pipeline_id': '6', 'state': 'RUNNING',
                       'cluster_id': '1027-061023-clasp844', 'name': 'Pipeline Demo NYCTaxi', 'health': 'HEALTHY'}],
         'pagination': {
             'next_page_token': 'page4',
             'prev_page_token': 'page3'}},
        {'statuses': [{'pipeline_id': '7', 'state': 'RUNNING',
                       'cluster_id': '1023-090256-woke18', 'name': 'Discovery Staging', 'health': 'HEALTHY'},
                      {'pipeline_id': '8', 'state': 'RUNNING', 'cluster_id': '1023-093334-cluck1',
                       'name': 'Very Large Pipeline', 'health': 'HEALTHY'}], 'pagination': {
            'prev_page_token': 'page4'}}
    ]

    runner = CliRunner()
    result = runner.invoke(cli.list_cli)
    assert pipelines_api_mock.list.call_count == 4
    pipelines_api_mock.list.assert_has_calls(
        [
            mock.call(),
            mock.call(page_token='page2'),
            mock.call(page_token='page3'),
            mock.call(page_token='page4')
        ], any_order=False)

    assert [status["pipeline_id"] for status in json.loads(result.stdout)] == ["1", "2", "3", "4", "5", "6", "7", "8"]
