<?php
/**
 * Файл настроек для модуля local_entrance_testing
 * 
 * @package    local_entrance_testing
 * @copyright  2024
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

if ($hassiteconfig) {
    $ADMIN->add('localplugins', new admin_externalpage(
        'local_entrance_testing',
        get_string('pluginname', 'local_entrance_testing'),
        new moodle_url('/local/entrance_testing/admin.php'),
        'moodle/site:config'
    ));
}
