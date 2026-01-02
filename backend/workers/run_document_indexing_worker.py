from common.workers.launcher import WorkerLauncher
from packages.documents.workers.document_indexing_worker import DocumentIndexingWorker

if __name__ == "__main__":
    from packages.companies.models.database.company import CompanyEntity  # noqa

    WorkerLauncher().run(
        worker_factory=DocumentIndexingWorker, worker_name="Document Indexing Worker"
    )
