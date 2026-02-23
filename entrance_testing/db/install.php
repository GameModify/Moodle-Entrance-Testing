<?php
/**
 * Файл установки модуля local_entrance_testing
 * 
 * @package    local_entrance_testing
 * @copyright  2024
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

/**
 * Функция установки модуля
 * 
 * @return bool
 */
function xmldb_local_entrance_testing_install() {
    global $CFG;
    
    // Устанавливаем значения по умолчанию
    set_config('api_url', 'http://localhost:8000/analyze-and-enroll', 'local_entrance_testing');
    set_config('entry_test_id', 2, 'local_entrance_testing');
    set_config('timeout', 30, 'local_entrance_testing');
    set_config('retry_attempts', 3, 'local_entrance_testing');
    
    return true;
}
