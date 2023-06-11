# Not actual test but demo using testing system
# Spawn worker pool before running the tests.
import time

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.background_jobs import get_queue, get_workers


def sleepy(duration=1):
	time.sleep(duration)


class TestOrchestrator(FrappeTestCase):
	def log_status(self):
		q = get_queue("default")
		workers = get_workers(q)
		worker_count = len(workers)
		jobs_count = len(q.get_job_ids())
		# Count running jobs too
		for w in workers:
			if w.get_current_job_id():
				jobs_count += 1
		print(f"{worker_count} | {jobs_count:03} ")

	def test_demo(self):
		print(f"# of Workers | # of Jobs")

		self.log_status()

		for _ in range(100):
			time.sleep(0.5)
			frappe.enqueue(sleepy)
			self.log_status()

		while True:
			time.sleep(0.5)
			self.log_status()
