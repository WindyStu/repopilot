from workflow import Job, State, advance


def test_pending_job_can_start():
    saved = []
    job = Job("job-1")

    assert advance(job, State.RUNNING, saved.append) is job
    assert saved == [job]
    assert job.state is State.RUNNING
