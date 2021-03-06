""" Starts home assistant. """
from __future__ import print_function

from multiprocessing import Process
import signal
import sys
import threading
import os
import argparse

from homeassistant import bootstrap
import homeassistant.config as config_util
from homeassistant.const import (__version__, EVENT_HOMEASSISTANT_START,
                                 RESTART_EXIT_CODE)


def validate_python():
    """ Validate we're running the right Python version. """
    major, minor = sys.version_info[:2]

    if major < 3 or (major == 3 and minor < 4):
        print("Home Assistant requires atleast Python 3.4")
        sys.exit(1)


def ensure_config_path(config_dir):
    """ Validates configuration directory. """

    lib_dir = os.path.join(config_dir, 'lib')

    # Test if configuration directory exists
    if not os.path.isdir(config_dir):
        if config_dir != config_util.get_default_config_dir():
            print(('Fatal Error: Specified configuration directory does '
                   'not exist {} ').format(config_dir))
            sys.exit(1)

        try:
            os.mkdir(config_dir)
        except OSError:
            print(('Fatal Error: Unable to create default configuration '
                   'directory {} ').format(config_dir))
            sys.exit(1)

    # Test if library directory exists
    if not os.path.isdir(lib_dir):
        try:
            os.mkdir(lib_dir)
        except OSError:
            print(('Fatal Error: Unable to create library '
                   'directory {} ').format(lib_dir))
            sys.exit(1)


def ensure_config_file(config_dir):
    """ Ensure configuration file exists. """
    config_path = config_util.ensure_config_exists(config_dir)

    if config_path is None:
        print('Error getting configuration path')
        sys.exit(1)

    return config_path


def get_arguments():
    """ Get parsed passed in arguments. """
    parser = argparse.ArgumentParser(
        description="Home Assistant: Observe, Control, Automate.")
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument(
        '-c', '--config',
        metavar='path_to_config_dir',
        default=config_util.get_default_config_dir(),
        help="Directory that contains the Home Assistant configuration")
    parser.add_argument(
        '--demo-mode',
        action='store_true',
        help='Start Home Assistant in demo mode')
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Start Home Assistant in debug mode. Runs in single process to '
        'enable use of interactive debuggers.')
    parser.add_argument(
        '--open-ui',
        action='store_true',
        help='Open the webinterface in a browser')
    parser.add_argument(
        '--skip-pip',
        action='store_true',
        help='Skips pip install of required packages on startup')
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Enable verbose logging to file.")
    parser.add_argument(
        '--pid-file',
        metavar='path_to_pid_file',
        default=None,
        help='Path to PID file useful for running as daemon')
    parser.add_argument(
        '--log-rotate-days',
        type=int,
        default=None,
        help='Enables daily log rotation and keeps up to the specified days')
    parser.add_argument(
        '--install-osx',
        action='store_true',
        help='Installs as a service on OS X and loads on boot.')
    parser.add_argument(
        '--uninstall-osx',
        action='store_true',
        help='Uninstalls from OS X.')
    parser.add_argument(
        '--restart-osx',
        action='store_true',
        help='Restarts on OS X.')
    if os.name != "nt":
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run Home Assistant as daemon')

    arguments = parser.parse_args()
    if os.name == "nt":
        arguments.daemon = False
    return arguments


def daemonize():
    """ Move current process to daemon process """
    # create first fork
    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    # decouple fork
    os.setsid()
    os.umask(0)

    # create second fork
    pid = os.fork()
    if pid > 0:
        sys.exit(0)


def check_pid(pid_file):
    """ Check that HA is not already running """
    # check pid file
    try:
        pid = int(open(pid_file, 'r').readline())
    except IOError:
        # PID File does not exist
        return

    try:
        os.kill(pid, 0)
    except OSError:
        # PID does not exist
        return
    print('Fatal Error: HomeAssistant is already running.')
    sys.exit(1)


def write_pid(pid_file):
    """ Create PID File """
    pid = os.getpid()
    try:
        open(pid_file, 'w').write(str(pid))
    except IOError:
        print('Fatal Error: Unable to write pid file {}'.format(pid_file))
        sys.exit(1)


def install_osx():
    """ Setup to run via launchd on OS X """
    with os.popen('which hass') as inp:
        hass_path = inp.read().strip()

    with os.popen('whoami') as inp:
        user = inp.read().strip()

    cwd = os.path.dirname(__file__)
    template_path = os.path.join(cwd, 'startup', 'launchd.plist')

    with open(template_path, 'r', encoding='utf-8') as inp:
        plist = inp.read()

    plist = plist.replace("$HASS_PATH$", hass_path)
    plist = plist.replace("$USER$", user)

    path = os.path.expanduser("~/Library/LaunchAgents/org.homeassistant.plist")

    try:
        with open(path, 'w', encoding='utf-8') as outp:
            outp.write(plist)
    except IOError as err:
        print('Unable to write to ' + path, err)
        return

    os.popen('launchctl load -w -F ' + path)

    print("Home Assistant has been installed. \
        Open it here: http://localhost:8123")


def uninstall_osx():
    """ Unload from launchd on OS X """
    path = os.path.expanduser("~/Library/LaunchAgents/org.homeassistant.plist")
    os.popen('launchctl unload ' + path)

    print("Home Assistant has been uninstalled.")


def setup_and_run_hass(config_dir, args, top_process=False):
    """
    Setup HASS and run. Block until stopped. Will assume it is running in a
    subprocess unless top_process is set to true.
    """
    if args.demo_mode:
        config = {
            'frontend': {},
            'demo': {}
        }
        hass = bootstrap.from_config_dict(
            config, config_dir=config_dir, daemon=args.daemon,
            verbose=args.verbose, skip_pip=args.skip_pip,
            log_rotate_days=args.log_rotate_days)
    else:
        config_file = ensure_config_file(config_dir)
        print('Config directory:', config_dir)
        hass = bootstrap.from_config_file(
            config_file, daemon=args.daemon, verbose=args.verbose,
            skip_pip=args.skip_pip, log_rotate_days=args.log_rotate_days)

    if args.open_ui:
        def open_browser(event):
            """ Open the webinterface in a browser. """
            if hass.config.api is not None:
                import webbrowser
                webbrowser.open(hass.config.api.base_url)

        hass.bus.listen_once(EVENT_HOMEASSISTANT_START, open_browser)

    hass.start()
    exit_code = int(hass.block_till_stopped())

    if not top_process:
        sys.exit(exit_code)
    return exit_code


def run_hass_process(hass_proc):
    """ Runs a child hass process. Returns True if it should be restarted.  """
    requested_stop = threading.Event()
    hass_proc.daemon = True

    def request_stop():
        """ request hass stop """
        requested_stop.set()
        hass_proc.terminate()

    try:
        signal.signal(signal.SIGTERM, request_stop)
    except ValueError:
        print('Could not bind to SIGTERM. Are you running in a thread?')

    hass_proc.start()
    try:
        hass_proc.join()
    except KeyboardInterrupt:
        request_stop()
        try:
            hass_proc.join()
        except KeyboardInterrupt:
            return False

    return (not requested_stop.isSet() and
            hass_proc.exitcode == RESTART_EXIT_CODE,
            hass_proc.exitcode)


def main():
    """ Starts Home Assistant. """
    validate_python()

    args = get_arguments()

    config_dir = os.path.join(os.getcwd(), args.config)
    ensure_config_path(config_dir)

    # os x launchd functions
    if args.install_osx:
        install_osx()
        return 0
    if args.uninstall_osx:
        uninstall_osx()
        return 0
    if args.restart_osx:
        uninstall_osx()
        install_osx()
        return 0

    # daemon functions
    if args.pid_file:
        check_pid(args.pid_file)
    if args.daemon:
        daemonize()
    if args.pid_file:
        write_pid(args.pid_file)

    # Run hass in debug mode if requested
    if args.debug:
        sys.stderr.write('Running in debug mode. '
                         'Home Assistant will not be able to restart.\n')
        exit_code = setup_and_run_hass(config_dir, args, top_process=True)
        if exit_code == RESTART_EXIT_CODE:
            sys.stderr.write('Home Assistant requested a '
                             'restart in debug mode.\n')
        return exit_code

    # Run hass as child process. Restart if necessary.
    keep_running = True
    while keep_running:
        hass_proc = Process(target=setup_and_run_hass, args=(config_dir, args))
        keep_running, exit_code = run_hass_process(hass_proc)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
