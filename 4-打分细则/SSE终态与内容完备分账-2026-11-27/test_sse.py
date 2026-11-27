import gzip
import unittest
from sse import BOM, projection, split_capture

FIN = b'data: {"choices":[{"finish_reason":"stop"}]}\n\n'
DONE = b'data: [DONE]\n\n'
BODY = FIN + DONE


def frame(event, data, eol=b'\n'):
    return b'event: ' + event + eol + b'data: ' + data + eol + eol


def terminal(status=b'completed', ident=b'A'):
    return frame(b'response.completed',
                 b'{"type":"response.completed","response":{"id":"' + ident
                 + b'","status":"' + status + b'"}}')


class TestEnvelope(unittest.TestCase):
    def codes(self, raw, family):
        return {r['code'] for r in projection(raw, family)['issues']}

    def test_equivalent_line_endings(self):
        for eol in (b'\n', b'\r', b'\r\n'):
            self.assertTrue(projection(BODY.replace(b'\n', eol), 'chat')['closed'])

    def test_multiline_payload_and_single_space(self):
        raw = b'data:  {"choices":\ndata: [{"finish_reason":"stop"}]}\n\n' + DONE
        self.assertTrue(projection(raw, 'chat')['closed'])
        self.assertEqual(split_capture(raw).frames[0].data,
                         b' {"choices":\n[{"finish_reason":"stop"}]}')

    def test_physical_alt_chars_in_json(self):
        for cp in ('\u2028', '\u2029', '\x85'):
            raw = ('data: {"x":"' + cp + '"}\n\n').encode()
            self.assertEqual(len(split_capture(raw).frames), 1)
            self.assertTrue(projection(FIN + raw + DONE, 'chat')['closed'])

    def test_comments_ids_and_bom(self):
        result = projection(b'\xef\xbb\xbf: hello\n\n' + BODY + b'id: hi\n\n: bye', 'chat')
        self.assertTrue(result['closed'])
        self.assertTrue(result['bom'])
        self.assertEqual(result['non_data_blocks'], 2)

    def test_single_initial_bom(self):
        for family, body in (('chat', BODY), ('codex', terminal())):
            for prefix in (b'', b': note\n\n', b'id: sample\n\n'):
                with self.subTest(family=family, prefix=prefix):
                    actual = projection(BOM + prefix + body, family)
                    self.assertTrue(actual['closed'])
                    self.assertEqual(actual['initial_bom_count'], 1)

    def test_repeated_initial_bom(self):
        for family, body in (('chat', BODY), ('codex', terminal())):
            for prefix in (b': note\n\n', b'id: sample\n\n'):
                for count in (2, 3):
                    with self.subTest(family=family, prefix=prefix, count=count):
                        actual = projection(BOM * count + prefix + body, family)
                        self.assertFalse(actual['closed'])
                        self.assertEqual(actual['initial_bom_count'], count)
                        self.assertIn({'code': 'REPEATED_INITIAL_BOM', 'line': 1}, actual['issues'])
                        self.assertEqual(len(actual['payloads']), 1)

    def test_internal_bom_is_not_initial(self):
        result = projection(FIN + b'data: {"x":"' + BOM + b'"}\n\n' + DONE, 'chat')
        self.assertTrue(result['closed'])
        self.assertEqual(result['initial_bom_count'], 0)
        self.assertEqual(len(result['payloads']), 2)

    def test_no_dispatch(self):
        for tail in (b'data: [DONE]', b'data: [DONE]\n'):
            r = projection(FIN + tail, 'chat')
            self.assertFalse(r['closed'])
            self.assertEqual(len(r['payloads']), 1)
            self.assertEqual(r['undispatched_data_lines'], 1)

    def test_data_after_terminal(self):
        self.assertIn('DATA_AFTER_NORMAL_TERMINAL', self.codes(BODY + FIN, 'chat'))
        self.assertIn('UNDISPATCHED_EOF_DATA', self.codes(BODY + b'data: {}', 'chat'))

    def test_repeated_terminal(self):
        self.assertIn('DUPLICATE_NORMAL_TERMINAL', self.codes(BODY + DONE, 'chat'))
        self.assertIn('DUPLICATE_NORMAL_TERMINAL', self.codes(terminal() * 2, 'codex'))

    def test_empty_data_is_payload_not_comment(self):
        self.assertIn('DATA_NOT_STRICT_OBJECT', self.codes(BODY + b'data:\n\n', 'chat'))
        self.assertIn('DATA_NOT_STRICT_OBJECT', self.codes(BODY + b'data\n\n', 'chat'))

    def test_finish_reason_and_usage(self):
        self.assertIn('CHAT_FINISH_NOT_SEEN', self.codes(b'data: {"choices":[]}\n\n' + DONE, 'chat'))
        self.assertTrue(projection(FIN + b'data: {"choices":[],"usage":{}}\n\n' + DONE,
                                   'chat')['closed'])

    def test_event_data_mismatch(self):
        r = terminal().replace(b'event: response.completed', b'event: response.created')
        self.assertIn('EVENT_DATA_TYPE_MISMATCH', self.codes(r, 'codex'))
        self.assertIn('EVENT_DATA_TYPE_MISMATCH', self.codes(r.split(b'\n', 1)[1], 'codex'))

    def test_responses_terminal_envelope(self):
        self.assertTrue(projection(terminal(), 'codex')['closed'])
        self.assertIn('TERMINAL_RESPONSE_STATUS', self.codes(terminal(b'incomplete'), 'codex'))
        self.assertIn('MISSING_RESPONSE_ID', self.codes(terminal(ident=b''), 'codex'))
        other = frame(b'response.created', b'{"type":"response.created","response":{"id":"B"}}')
        self.assertIn('RESPONSE_ID_SPLIT', self.codes(other + terminal(), 'codex'))
        other = frame(b'response.failed', b'{"type":"response.failed"}')
        self.assertIn('NON_NORMAL_TERMINAL', self.codes(other + terminal(), 'codex'))

    def test_malformed_json_and_duplicate_key(self):
        for v in (b'{"x":1,"x":2}', b'{"x":NaN}', b'false', b'{'):
            self.assertIn('DATA_NOT_STRICT_OBJECT', self.codes(FIN + b'data: ' + v + b'\n\n' + DONE, 'chat'))

    def test_invalid_utf8_is_unknown(self):
        r = projection(BODY + b'\xff', 'chat')
        self.assertFalse(r['closed'])
        self.assertIsNone(r['undispatched_data_lines'])
        self.assertEqual(r['issues'][0]['code'], 'INVALID_UTF8')

    def test_gzip_truncation_is_not_plaintext(self):
        encoded = gzip.compress(BODY, mtime=0)
        self.assertEqual(gzip.decompress(encoded), BODY)
        with self.assertRaises((EOFError, OSError)):
            gzip.decompress(encoded[:-1])

    def test_duplicate_event_field(self):
        r = terminal().replace(b'event: ', b'event: hidden\nevent: ', 1)
        self.assertIn('REPEATED_EVENT_FIELD', self.codes(r, 'codex'))

    def test_whitespace_before_field_not_normalized(self):
        self.assertIn('MISSING_NORMAL_TERMINAL', self.codes(FIN + b' ' + DONE, 'chat'))
        self.assertIn('DATA_NOT_STRICT_OBJECT', self.codes(FIN + b'data:  [DONE]\n\n', 'chat'))


if __name__ == '__main__':
    unittest.main()
