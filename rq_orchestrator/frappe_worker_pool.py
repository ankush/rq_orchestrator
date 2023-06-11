import os
import time

import frappe
from rq import Worker
from rq.command import send_shutdown_command
from rq.worker import WorkerStatus
from rq.worker_pool import WorkerPool


class FrappeWorkerPool(WorkerPool):
	def __init__(
		self,
		*args,
		min_workers: int = 1,
		max_workers: int = 8,
		utilization_threshold=0.5,
		scaling_period=10,  # seconds
		**kwargs,
	):
		self._min_workers = min_workers
		kwargs["num_workers"] = min_workers
		self._max_workers = max_workers
		self._utilization_threshold = utilization_threshold
		self._scaling_period = scaling_period
		self._workers_killed = set()

		# Map of last known utilization time
		self._utilization_history = {}

		super().__init__(*args, **kwargs)

	def check_workers(self, *args, **kwargs):
		super().check_workers(*args, **kwargs)
		self.apply_scaling()
		time.sleep(self._scaling_period)

	def get_average_utilization(self, workers: list[Worker]) -> float:
		utilizations = []
		for worker in workers:
			if recent_utilization := self.get_worker_utilization(worker):
				utilizations.append(recent_utilization)

		if not utilizations:
			return 0.0

		return sum(utilizations) / len(utilizations)

	def _get_workers_in_pool(self):
		return [
			w for w in Worker.all(connection=self.connection) if w.name in self.worker_dict
		]

	def get_worker_utilization(self, worker: Worker) -> float | None:
		"""Get worker's utilization in previous scaling period,

		If worker was spawned in last period then it is not considered"""

		current_working_time = worker.total_working_time
		last_known_working_time = self._utilization_history.get(worker.name)
		self._utilization_history[worker.name] = current_working_time

		if last_known_working_time is None:
			return

		# HACK/XXX: If there's long running job the total working time wont be updated but
		# we should consider it 100% utilization.
		if (
			worker.get_state() == WorkerStatus.BUSY
			and current_working_time == last_known_working_time
		):
			return 1.0

		return (current_working_time - last_known_working_time) / self._scaling_period

	def apply_scaling(self):
		workers = self._get_workers_in_pool()
		utilization = self.get_average_utilization(workers)

		if utilization > self._utilization_threshold and self.num_workers < self._max_workers:
			# WorkerPool handles scaling up automatically, not designed to but "works"
			self.num_workers += 1
			self.log.info(
				f"Utilization at {utilization}, increased worker count to {self.num_workers}"
			)
		# Spawn down only occurs at 1/2 of threshold to avoid continuously spawning up/down
		elif (
			utilization < self._utilization_threshold / 2
			and self.num_workers > self._min_workers
		):
			self.attempt_scale_down(workers)
			self.log.info(
				f"Utilization at {utilization}, decreased worker count to {self.num_workers}"
			)
		else:
			self.log.debug(f"Utilization {utilization} within limits, scaling not applied.")

	def attempt_scale_down(self, workers: list[Worker]):
		# Attempt to kill first idle worker
		for worker in workers:
			if worker.get_state() == WorkerStatus.IDLE and worker.total_working_time:
				# kill this one
				self.kill_worker(worker)
				return

	def kill_worker(self, worker: Worker):
		# Repeatedly sending sigint will result in forceful termination,
		# hence only send singal once.
		if worker.name not in self._workers_killed:
			self.num_workers -= 1
			send_shutdown_command(self.connection, worker.name)
			self._utilization_history.pop(worker.name, None)
			self._workers_killed.add(worker.name)


def start_worker_pool(
	queue: str | None = None,
	min_workers: int = 1,
	max_workers: int = 8,
	scaling_period: int = 10,
	utilization_threshold: float = 0.5,
):
	from frappe.utils.background_jobs import get_queue_list, get_redis_conn

	with frappe.init_site():
		# empty init is required to get redis_queue from common_site_config.json
		redis_connection = get_redis_conn()

		if queue:
			queue = [q.strip() for q in queue.split(",")]
		queues = get_queue_list(queue, build_queue_name=True)

	pool = FrappeWorkerPool(
		queues=queues,
		connection=redis_connection,
		min_workers=min_workers,
		max_workers=max_workers,
		scaling_period=scaling_period,
		utilization_threshold=utilization_threshold,
	)
	pool.start()
