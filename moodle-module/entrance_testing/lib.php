<?php
defined('MOODLE_INTERNAL') || die();

/**
 * Observer for mod_quiz attempt_graded event.
 * Only writes minimal data to queue table (no external requests here).
 *
 * @param \mod_quiz\event\attempt_graded $event
 * @return void
 */
function local_entrance_testing_observer_attempt_graded(\mod_quiz\event\attempt_graded $event) {
    global $DB;

    try {
        $attempt = $event->get_record_snapshot('quiz_attempts', $event->objectid);
        $quiz    = $event->get_record_snapshot('quiz', $event->other['quizid']);

        if (!$attempt || !$quiz) {
            error_log("[EntranceTesting] No attempt or quiz snapshot (attempt={$event->objectid})");
            return;
        }

        // Only for configured entry test
        $entry_test_id = (int)get_config('local_entrance_testing', 'entry_test_id');
        if ($entry_test_id <= 0) {
            error_log("[EntranceTesting] entry_test_id not configured");
            return;
        }
        if ((int)$quiz->id !== $entry_test_id) {
            return;
        }

        // Ensure attempt is finished
        if ((string)$attempt->state !== 'finished') {
            error_log("[EntranceTesting] Attempt not finished (id={$attempt->id}, state={$attempt->state})");
            return;
        }

        // Insert into queue table. Avoid duplicates: check by attemptid
        $exists = $DB->get_record('local_entrance_testing_queue', ['attemptid' => $attempt->id], 'id', IGNORE_MULTIPLE);
        if ($exists) {
            // already queued
            return;
        }

        $record = new stdClass();
        $record->userid = (int)$attempt->userid;
        $record->quizid = (int)$quiz->id;
        $record->attemptid = (int)$attempt->id;
        $record->state = $DB->get_field_sql('SELECT state FROM {quiz_attempts} WHERE id = ?', [$attempt->id]) ?: $attempt->state;
        $record->timecreated = time();
        $record->timesent = 0;
        $record->status = '';
        $record->attempts = 0;

        $DB->insert_record('local_entrance_testing_queue', $record);
        // no external requests here
    } catch (Throwable $e) {
        error_log("[EntranceTesting] Exception in observer: " . $e->getMessage());
    }
}


/**
 * Send single queue record to external API.
 * This is safe to call from scheduled task (cron).
 *
 * Returns true on success, false otherwise.
 *
 * @param stdClass $queue_record record from local_entrance_testing_queue
 * @return bool
 */
function local_entrance_testing_send_queue_record(stdClass $queue_record): bool {
    global $DB;

    $api_url = trim(get_config('local_entrance_testing', 'api_url'));
    if (empty($api_url)) {
        $DB->update_record('local_entrance_testing_queue', (object)[
            'id' => $queue_record->id,
            'status' => 'no_api_url',
            'timesent' => 0,
            'attempts' => $queue_record->attempts + 1
        ]);
        error_log("[EntranceTesting] API URL not configured");
        return false;
    }

    // Prepare payload: you can expand this with more fields if needed
    $payload = [
        'user_id' => (int)$queue_record->userid,
        'quiz_id' => (int)$queue_record->quizid,
        'attempt_id' => (int)$queue_record->attemptid,
        'attempt_state' => $queue_record->state,
        'time_queued' => (int)$queue_record->timecreated,
    ];
    $json = json_encode($payload, JSON_UNESCAPED_UNICODE);

    $timeout = (int)(get_config('local_entrance_testing', 'timeout') ?: 15);
    $maxretries = (int)(get_config('local_entrance_testing', 'retry_attempts') ?: 3);

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $api_url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $json);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
    // For dev/local you may disable peer verify, but in production enable it
    $verify = (int)(get_config('local_entrance_testing', 'ssl_verify') ?: 0);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, (bool)$verify);
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, $verify ? 2 : 0);

    $success = false;
    $laststatus = '';
    for ($i = 1; $i <= $maxretries; $i++) {
        $response = curl_exec($ch);
        $errno = curl_errno($ch);
        $err = $errno ? curl_error($ch) : '';
        $http = curl_getinfo($ch, CURLINFO_HTTP_CODE);

        if ($errno) {
            $laststatus = "curl_err:{$errno}";
            error_log("[EntranceTesting] curl error attempt {$i} for attempt {$queue_record->attemptid}: {$err}");
            sleep(1);
            continue;
        }

        if ($http >= 500) {
            $laststatus = "http_{$http}";
            error_log("[EntranceTesting] server error HTTP {$http} attempt {$i} for attempt {$queue_record->attemptid}");
            sleep(1);
            continue;
        }

        // HTTP 200 (or 201) — interpret response
        if ($http >= 200 && $http < 300) {
            $decoded = json_decode($response, true);
            if (is_array($decoded) && !empty($decoded['success'])) {
                $success = true;
                $laststatus = 'ok';
                break;
            }
            // If API doesn't return 'success', store response for diagnostics
            $laststatus = 'resp:' . substr($response, 0, 200);
            error_log("[EntranceTesting] API response for attempt {$queue_record->attemptid}: {$response}");
            break;
        }

        // Client errors — stop retrying
        if ($http >= 400 && $http < 500) {
            $laststatus = "http_{$http}";
            error_log("[EntranceTesting] client HTTP {$http} for attempt {$queue_record->attemptid}: {$response}");
            break;
        }

        $laststatus = "unknown_http_{$http}";
        break;
    }

    curl_close($ch);

    // Update queue record
    $update = new stdClass();
    $update->id = $queue_record->id;
    $update->attempts = $queue_record->attempts + 1;
    $update->timesent = $success ? time() : 0;
    $update->status = $laststatus;
    $DB->update_record('local_entrance_testing_queue', $update);
    \core\task\manager::queue_adhoc_task(
        new \local_entrance_testing\task\send_queue_records_adhoc()
    );
    return $success;
}


/**
 * Check API health by sending a test request.
 * 
 * @return array with 'status' and 'message' keys
 */
function local_entrance_testing_check_api_health(): array {
    $api_url = trim(get_config('local_entrance_testing', 'api_url'));
    if (empty($api_url)) {
        return [
            'status' => 'error',
            'message' => 'API URL not configured'
        ];
    }

    $timeout = (int)(get_config('local_entrance_testing', 'timeout') ?: 15);
    $verify = (int)(get_config('local_entrance_testing', 'ssl_verify') ?: 0);

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $api_url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode(['test' => true]));
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, (bool)$verify);
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, $verify ? 2 : 0);

    $response = curl_exec($ch);
    $errno = curl_errno($ch);
    $err = $errno ? curl_error($ch) : '';
    $http = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($errno) {
        return [
            'status' => 'error',
            'message' => "cURL error: {$err}"
        ];
    }

    if ($http >= 200 && $http < 300) {
        $decoded = json_decode($response, true);
        return [
            'status' => 'ok',
            'message' => 'Connection successful',
            'data' => $decoded
        ];
    }

    return [
        'status' => 'error',
        'message' => "HTTP {$http}: " . substr($response, 0, 200)
    ];
}