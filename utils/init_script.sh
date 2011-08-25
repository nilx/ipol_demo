#!/bin/sh -e
#
# System-V init script to start or stop the IPOL demo service
#

### BEGIN INIT INFO
# Provides:          ipol-demo
# Required-Start:    $all
# Required-Stop:     $all
# Should-Start:      
# Should-Stop:       
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: start and stop the IPOL demo service
# Description:       
### END INIT INFO

BASEDIR=/srv/ipol
SCRIPT=${BASEDIR}/demo/demo.py
SCRIPTNAME=${SCRIPT##*/}
SUID=www-data
PIDFILE=${BASEDIR}/demo.pid

test -x $SCRIPT || exit 0

. /lib/lsb/init-functions

export CCACHE_DIR=/tmp/.ccache

case "$1" in
    start)
	log_daemon_msg "Starting IPOL demo" "${SCRIPT}"
	/sbin/start-stop-daemon --start --oknodo \
	    --user ${SUID} --name ${SCRIPTNAME} \
	    --pidfile ${PIDFILE} --make-pidfile \
	    --startas ${SCRIPT} \
	    --chuid ${SUID} --background -- build run
	sleep 1
	PID=$(cat ${PIDFILE})
	if [ -f /proc/$PID/stat ]; then
	    # the demo server is running
	    log_end_msg 0
	else
	    # the demo server failed to start
	    log_end_msg 1
	    rm ${PIDFILE}
	    exit 1
	fi
    ;;

    stop)
	log_daemon_msg "Stopping IPOL demo" "${SCRIPT}"
	/sbin/start-stop-daemon --stop --oknodo \
	    --user ${SUID} --name ${SCRIPTNAME} --pidfile ${PIDFILE} \
	    --retry 5
	if [ ! -f ${PIDFILE} ]; then
	    log_end_msg 0
	    log_daemon_msg "PID file not found"
	    log_end_msg 0
	    exit 0
	else
	    PID=$(cat ${PIDFILE})
	    if [ -f /proc/$PID/stat ]; then
		log_end_msg 1
		exit 1
	    else
		log_end_msg 0
		rm ${PIDFILE}
	    fi
	fi
    ;;

    status)
	if [ -f ${PIDFILE} ]; then
	    PID=$(cat ${PIDFILE})
	    if [ -f /proc/$PID/stat ]; then
		echo "running"
	    else
		echo "not running"
		rm ${PIDFILE}
	    fi
	else
	    echo "not running"
	fi
    ;;

    restart)
        $0 stop
        $0 start
    ;;

    *)
	log_action_msg "Usage: $0 {start|stop|restart|status}"
	log_end_msg 1
	exit 1
    ;;
esac

exit 0
