<?php
namespace local_entrance_testing\task;

defined('MOODLE_INTERNAL') || die();

class send_queue_records_adhoc extends \core\task\adhoc_task {
    public function execute() {
        global $DB;
        $records = $DB->get_records('local_entrance_testing_queue', ['timesent' => 0]);
        foreach ($records as $rec) {
            \local_entrance_testing_send_queue_record($rec);
        }
    }
}
