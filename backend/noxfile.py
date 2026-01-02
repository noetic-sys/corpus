import nox

PYTHON_VERSION = "3.11"


@nox.session(python=PYTHON_VERSION)
def tests(session):
    session.run("poetry", "install", external=True)
    session.run("poetry", "run", "pytest", "tests/unit", external=True)


@nox.session(python=PYTHON_VERSION)
def lint(session):
    session.run("poetry", "install", external=True)
    session.run("poetry", "run", "ruff", "check", ".", external=True)


# @nox.session(python=PYTHON_VERSION)
# def type(session):
#    session.run("poetry", "install", external=True)
#    session.run("poetry", "run", "mypy", "app", external=True)


@nox.session(python=PYTHON_VERSION)
def format(session):
    session.run("poetry", "install", external=True)
    session.run("poetry", "run", "black", "--check", "api", "common", "packages", "workers", external=True)
    session.run("poetry", "run", "ruff", "check", ".", external=True)
