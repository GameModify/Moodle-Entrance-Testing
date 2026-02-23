<?php
/**
 * Страница настроек модуля local_entrance_testing
 * 
 * @package    local_entrance_testing
 * @copyright  2024
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

require_once('../../config.php');
require_once($CFG->libdir.'/adminlib.php');

$PAGE->set_url('/local/entrance_testing/admin.php');
$PAGE->set_context(context_system::instance());
$PAGE->set_pagelayout('admin');
$PAGE->set_title(get_string('settings', 'local_entrance_testing'));
$PAGE->set_heading(get_string('settings', 'local_entrance_testing'));

require_login();
require_capability('moodle/site:config', context_system::instance());

// Обработка формы
if ($data = data_submitted() && confirm_sesskey()) {
    if (isset($data->api_url)) {
        set_config('api_url', $data->api_url, 'local_entrance_testing');
    }
    if (isset($data->entry_test_id)) {
        set_config('entry_test_id', $data->entry_test_id, 'local_entrance_testing');
    }
    if (isset($data->timeout)) {
        set_config('timeout', $data->timeout, 'local_entrance_testing');
    }
    if (isset($data->retry_attempts)) {
        set_config('retry_attempts', $data->retry_attempts, 'local_entrance_testing');
    }
    
    redirect($PAGE->url, get_string('settings_saved', 'local_entrance_testing'), null, \core\output\notification::NOTIFY_SUCCESS);
}

// Обработка тестирования соединения
$connection_result = null;
if (optional_param('test_connection', false, PARAM_BOOL)) {
    require_once($CFG->dirroot . '/local/entrance_testing/lib.php');
    $connection_result = local_entrance_testing_check_api_health();
}

echo $OUTPUT->header();

echo $OUTPUT->heading(get_string('entrance_testing', 'local_entrance_testing'));

// Форма настроек
$form = new stdClass();
$form->api_url = get_config('local_entrance_testing', 'api_url') ?: 'http://localhost:8000/analyze-and-enroll';
$form->entry_test_id = get_config('local_entrance_testing', 'entry_test_id') ?: 2;
$form->timeout = get_config('local_entrance_testing', 'timeout') ?: 30;
$form->retry_attempts = get_config('local_entrance_testing', 'retry_attempts') ?: 3;

echo html_writer::start_tag('form', array('method' => 'post', 'action' => $PAGE->url));
echo html_writer::empty_tag('input', array('type' => 'hidden', 'name' => 'sesskey', 'value' => sesskey()));

echo html_writer::start_tag('table', array('class' => 'generaltable'));
echo html_writer::start_tag('tr');
echo html_writer::tag('td', get_string('api_url', 'local_entrance_testing') . ':');
echo html_writer::tag('td', html_writer::empty_tag('input', array(
    'type' => 'text',
    'name' => 'api_url',
    'value' => $form->api_url,
    'size' => 60
)));
echo html_writer::end_tag('tr');

echo html_writer::start_tag('tr');
echo html_writer::tag('td', get_string('entry_test_id', 'local_entrance_testing') . ':');
echo html_writer::tag('td', html_writer::empty_tag('input', array(
    'type' => 'number',
    'name' => 'entry_test_id',
    'value' => $form->entry_test_id,
    'min' => 1
)));
echo html_writer::end_tag('tr');

echo html_writer::start_tag('tr');
echo html_writer::tag('td', get_string('timeout', 'local_entrance_testing') . ':');
echo html_writer::tag('td', html_writer::empty_tag('input', array(
    'type' => 'number',
    'name' => 'timeout',
    'value' => $form->timeout,
    'min' => 5,
    'max' => 300
)));
echo html_writer::end_tag('tr');

echo html_writer::start_tag('tr');
echo html_writer::tag('td', get_string('retry_attempts', 'local_entrance_testing') . ':');
echo html_writer::tag('td', html_writer::empty_tag('input', array(
    'type' => 'number',
    'name' => 'retry_attempts',
    'value' => $form->retry_attempts,
    'min' => 1,
    'max' => 10
)));
echo html_writer::end_tag('tr');

echo html_writer::end_tag('table');

echo html_writer::tag('p', html_writer::empty_tag('input', array(
    'type' => 'submit',
    'value' => get_string('save_changes', 'local_entrance_testing'),
    'class' => 'btn btn-primary'
)));

echo html_writer::end_tag('form');

// Кнопка тестирования соединения
echo html_writer::tag('hr', '');
echo html_writer::start_tag('form', array('method' => 'get', 'action' => $PAGE->url));
echo html_writer::empty_tag('input', array('type' => 'hidden', 'name' => 'test_connection', 'value' => '1'));
echo html_writer::empty_tag('input', array(
    'type' => 'submit',
    'value' => get_string('test_connection', 'local_entrance_testing'),
    'class' => 'btn btn-secondary'
));
echo html_writer::end_tag('form');

// Результат тестирования соединения
if ($connection_result !== null) {
    echo html_writer::tag('hr', '');
    if ($connection_result['status'] === 'ok') {
        echo $OUTPUT->notification(get_string('connection_success', 'local_entrance_testing'), 'notifysuccess');
        if (isset($connection_result['data'])) {
            echo html_writer::tag('pre', json_encode($connection_result['data'], JSON_PRETTY_PRINT));
        }
    } else {
        echo $OUTPUT->notification(get_string('connection_failed', 'local_entrance_testing') . ': ' . $connection_result['message'], 'notifyerror');
    }
}

echo $OUTPUT->footer();
