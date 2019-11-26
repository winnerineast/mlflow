import mock
import pytest

from mlflow.entities import FileInfo
from mlflow.store.artifact.artifact_repo import ArtifactRepository


class ArtifactRepositoryImpl(ArtifactRepository):

    def log_artifact(self, local_file, artifact_path=None):
        raise NotImplementedError()

    def log_artifacts(self, local_dir, artifact_path=None):
        raise NotImplementedError()

    def list_artifacts(self, path):
        raise NotImplementedError()

    def _download_file(self, remote_file_path, local_path):
        print("download_file called with ", remote_file_path)


@pytest.mark.parametrize("base_uri, download_arg, list_return_val", [
    ('12345/model', '', ['modelfile']),
    ('12345/model', '', ['.', 'modelfile']),
    ('12345', 'model', ['model/modelfile']),
    ('12345', 'model', ['model', 'model/modelfile']),
    ('', '12345/model', ['12345/model/modelfile']),
    ('', '12345/model', ['12345/model', '12345/model/modelfile']),
])
def test_download_artifacts_does_not_infinitely_loop(base_uri, download_arg, list_return_val):

    def list_artifacts(path):
        if path.endswith("model"):
            return [FileInfo(item, False, 123) for item in list_return_val]
        else:
            return []

    with mock.patch.object(ArtifactRepositoryImpl, "list_artifacts") as list_artifacts_mock:
        list_artifacts_mock.side_effect = list_artifacts
        repo = ArtifactRepositoryImpl(base_uri)
        repo.download_artifacts(download_arg)
