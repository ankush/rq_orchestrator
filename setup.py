from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in rq_orchestrator/__init__.py
from rq_orchestrator import __version__ as version

setup(
	name="rq_orchestrator",
	version=version,
	description="Providers RQ worker pool with dynamic scaling",
	author="Ankush Menat",
	author_email="ankush@frappe.io",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
