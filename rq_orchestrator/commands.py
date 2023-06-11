import click


@click.command("worker-pool")
@click.option(
	"--queue",
	type=str,
	help="Queue to consume from. Multiple queues can be specified using comma-separated string. If not specified all queues are consumed.",
)
@click.option("--min-workers", type=int, default=1, help="Minimum worker count")
@click.option("--max-workers", type=int, default=8, help="maximum worker count")
@click.option(
	"--scaling-period",
	type=int,
	default=10,
	help="Time in seconds after which autoscaling should run.",
)
@click.option(
	"--utilization-threshold",
	type=float,
	default=0.5,
	help="Utilization after which workers should be scaled up.",
)
def start_worker_pool(
	queue, min_workers, max_workers, scaling_period, utilization_threshold
):
	"""Start a backgrond worker pool"""
	from rq_orchestrator.frappe_worker_pool import start_worker_pool

	start_worker_pool(
		queue,
		max_workers=max_workers,
		min_workers=min_workers,
		scaling_period=scaling_period,
		utilization_threshold=utilization_threshold,
	)


commands = [
	start_worker_pool,
]
