<?php
namespace local_entrance_testing\task;

require_once(__DIR__ . '/../../lib.php');


defined('MOODLE_INTERNAL') || die();

class send_queue_records extends \core\task\scheduled_task {

    public function get_name(): string {
        return get_string('sendqueue', 'local_entrance_testing');
    }

    public function execute(): void {
        global $DB;

        $records = $DB->get_records('local_entrance_testing_queue', ['timesent' => 0]);
        foreach ($records as $rec) {
            \local_entrance_testing_send_queue_record($rec);
        }
    }
}
