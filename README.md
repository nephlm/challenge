#Verodin Challenge

If something hasn't gone awry, You should be able to start the CC
instance in the Virginia region.  Once it is up connect to the web
interface at:

`http://<public_ip>:8317/`

From there spin up some workers from the top section by selecting a
regions and pressing `start`.  Since they are
configured on the fly and this turned out to need a newer version of
Python it will take several minutes after the nodes are running before
they start processing jobs.  They will be ready when `cc2w` and `w2cc`,
the communication checks, are complete and labeled as True.

Paste a list of URLs into the middle section and press `submit`.
Once the workers are up, they will start processing the queue.

Results are stored in the DB, but there is no particular way of
getting access to that from the front end.  Once a given URL has been
submitted to the queue subsequent submissions of the same URL will
be (silently) dropped.

Any URLs that can't be processed (Bad format (not really a URL), no
server or offline, results that can't be processed) will be re-added
with a cleans state to try again.  Any such broken links at the end
will juggle around and play havok with the queue numbers as they're
continuously retried.

###Starting points

* `src/cc.py` is the entry point into the controller and
`src/worker/worker.py` is the entry point into the worker.
* Each directory has a `install.sh`
  * in the case of `src/worker` it  is exactly what is done
to configure the worker (plus `generateScript()` in
`ccLib.py`.
  * In the case of `src` it is more helpful reminders.


##Not Yet Handled:

Major things that aren't handled in this version of the challenge.  I'm
sure there are many more minor things, but these are major items.

* Security: There is nothing ensuring that only designated workers
get jobs from the CC, or any other web call.  This means random
webcalls can bring up or take down AWS instances associated with
the account. Obviously this isn't ready for anything but a proof of
concept phase.
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
* AWS Failures: Proper handling of credential, rate limit, eventually
consistent, clock inconsistency and other edge cases when dealing with
AWS are ignored with may cause failures to launch or terminate workers
or display of stale data.  These issues are usually only solvable by
an error reporting mechanism, which doesn't exist yet.

###UI

* When the queue is down to just URLs that cant' be processed, the
numbers will fluctuate.
* When adding URLs that have already been processed, they will be
dropped without any user feedback.
* No feedback about the state of nodes coming up (which takes too long
since Python 2.7.12 is compiled during the config phase.)

###Quirks

* The keypair names are not uniquified, so if multiple CCs are up, unless the files are copied, they will delete each others keys
that Amazon stores, making sshing into new instances impossible.
