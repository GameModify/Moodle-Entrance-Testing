<?php
defined('MOODLE_INTERNAL') || die();

$tasks = [
    [
        'classname' => 'local_entrance_testing\task\send_queue_records',
        'blocking'  => 0,
        // frequency in seconds, e.g. run every 60 seconds (cron runs periodically)
        'minute'    => '*',
        'hour'      => '*',
        'day'       => '*',
        'dayofweek' => '*',
        'month'     => '*'
    ],
];
