"""
state management example - stop, start, and wait for ChildProcess to finish

Creates a ChildProcess that sleeps for 5s, during which time the process is
stopped, then started, then terminated.
"""

from childprocess import ChildProcessBuilder as CPB

def main():
    print("Spawning sleeper...")
    sleeper = CPB("sleep 5s").spawn()
    if sleeper:
        print("Spawned sleeper.")
    if not sleeper:
        print("Sleeper did not spawn. Aborting.")
        return

    print("Making sure sleeper is running...")
    if sleeper.is_running():
        print("Sleeper is running.")
    else:
        print("Sleeper is not running. Aborting.")
        return

    print("Stopping sleeper...")
    sleeper.stop()
    if sleeper.is_stopped():
        print("Sleeper is stopped.")
    else:
        print("Sleeper is not stopped. Aborting.")
        return

    print("Starting sleeper again...")
    sleeper.start()
    if sleeper.is_running():
        print("Sleeper is started.")
    else:
        print("Sleeper did not restart. Aborting.")
        return

    print("Waiting for sleeper to finish...")
    sleeper.wait_for_finish()
    if sleeper.is_finished():
        print("Sleeper is finished.")
    else:
        print("Sleeper is not finished, but it should be.")

    return

if __name__ == "__main__":
    main()
