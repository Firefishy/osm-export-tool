update export_runs
set status = 'FAILED'
where created_at < NOW() - INTERVAL '1 days' and status = 'SUBMITTED'