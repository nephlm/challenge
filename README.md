# verodin
Verodin Challenge



Not Yet Handled:

Major things that aren't handled in this version of the challenge.  I'm
sure there are many more minor things, but these are major items.

* Job Recovery:  If a worker is taken off line, either by unhandled
exception of user action, the task they were working on still appears to
be working.  A process to reap such abandoned processes and return the
work to the queue needs to be implemented.
* Request identification: At present anyone can pretend to be a worker or
the ui and request a job or spin up/take down worker nodes.  A token
needs to be put in place to make someone doing such spoofing do more work.
* Error reporting: At present no sort of user feedback is provided for
issues. Some sort of feedback on the ui or at least logs should be
implemented.
*AWS Failures: Proper handling of credential, rate limit, eventually
consistent, clock inconsistency and other edge cases when dealing with
AWS are ignored with may cause failures to launch or terminate workers
or display of stale data.  These issues are usually only solvable by
an error reporting mechanism, which doesn't exist yet.
