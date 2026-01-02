from common.workers.launcher import WorkerLauncher
from packages.qa.workers.qa_worker import QAWorker

if __name__ == "__main__":
    from packages.companies.models.database.company import CompanyEntity  # noqa

    WorkerLauncher().run(worker_factory=QAWorker, worker_name="QA Worker")
