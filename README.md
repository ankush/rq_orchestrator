## RQ Orchestrator

Provides RQ worker pool with dynamic scaling :rocket:

WARNING: Experimental POC. Don't run this anywhere near production sites.

### Concept

There are roughly two metrics that need to be optimized while deciding on worker count:

1. Memory usage - More # of workers => more memory usage.
2. Average wait time for jobs ~ How responsive the system is.

Both of these are at odds with each other as a responsive system would require
more workers i.e. more memory usage. We need to dynamically spawn workers while
still control what parameters to optimize for.

### Implementation

This app provides a command to start worker pool instead of single worker.

Example:

First remove all `bench worker` processes from process list and supervisor conf and replace them with equivalent commands for worker pool.

```
bench worker-pool --min-workers=2 --max-workers=5 --scaling-period=5 --utilization-threshold=0.5
```

This command will:

-   Spawn two workers and start working
-   Every 5 seconds:
    -   Check how much time workers spent in last 30 seconds
    -   If it was more than `--utilization-threshold` i.e. 50% then increase
        one worker.
    -   If it was less than half of threshold i.e. 25% then it will decrease
        one worker.
    -   If it was within 25-50% range worker pool stays as is.

Test it out by simulating fake workload from bench console:

```python
# A function that just sleeps
from frappe.core.doctype.rq_job.test_rq_job import test_func

while True:
	import time
	time.sleep(0.5)
	frappe.enqueue(test_func, sleep=1)
```

-   This will enqueue 2 jobs every second that consume 1 second each,=
-   So roughly we will end up spewing 4-5 workers at which point workload and
    workers are balanced according to set parameters.
-   If you stop enqueuing new jobs, overtime it will drop back to 2 workers
    again.
-   To Monitor this in realtime go to `RQ Worker` doctype and setup
    auto-refresh:
    -   `setInterval(() => {cur_list.refresh()}, 1000)`


If you visualize this is roughly how it will look:

![image](https://github.com/ankush/rq_orchestrator/assets/9079960/650649e2-c359-4f68-99be-e846d7c39978)


### Implementation notes

-   `--utilization-threshold` controls responsiveness vs efficiency. Low
    threshold means highly responsive system but very low efficiency and vice
    versa.
-   Some weird edge cases are handled weirdly.
    -   Extremely long running jobs which might not increase utilization if they
        started before scaling window but didn't end yet.
-   Utilization in time bucket is computed by remembering old utilization. This
    isn't accurate at all and requires rework.
-   Scaling up and down only happens in unit of 1 worker.
-   Scale down happens at half the threshold for scale up. If you're familiar
    with idea of table doubling or resizeable arrays, this is similar concept
    to avoid repeated scale up/downs which are of no use.

#### License

MIT
