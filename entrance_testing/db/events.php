<?php
defined('MOODLE_INTERNAL') || die();

$observers = [
    [
        'eventname'  => '\mod_quiz\event\attempt_graded',
        'callback'   => 'local_entrance_testing_observer_attempt_graded',
        'includefile'=> '/local/entrance_testing/lib.php',
    ],
];
