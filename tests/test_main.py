import json
import unittest

import main


class FakeResponse:
    def __init__(self, body):
        self.text = body

    def json(self):
        return json.loads(self.text)


def trpc_batch_body(data, ensure_ascii=True):
    return json.dumps([{'result': {'data': data}}], ensure_ascii=ensure_ascii)


class ParseTrpcResponseTest(unittest.TestCase):
    def test_parses_body_containing_line_separator_character(self):
        # regression: the events.hostEventSearch body is a single line of JSON,
        # but description strings may contain U+2028, which str.splitlines()
        # treats as a line break, so the body must be parsed whole
        events = [{'name': 'first', 'description': 'a\u2028b'}]
        body = trpc_batch_body({'events': events}, ensure_ascii=False)

        self.assertTrue('\u2028' in body)
        self.assertEqual(main.parse_trpc_response(FakeResponse(body)), {'events': events})

    def test_parses_body_without_newlines(self):
        body = trpc_batch_body({'events': []})

        self.assertEqual(main.parse_trpc_response(FakeResponse(body)), {'events': []})

    def test_raises_on_error_envelope(self):
        body = json.dumps([{'error': {'message': 'Unauthorized'}}])

        with self.assertRaises(ValueError):
            main.parse_trpc_response(FakeResponse(body))

    def test_raises_on_unexpected_body(self):
        with self.assertRaises(ValueError):
            main.parse_trpc_response(FakeResponse('null'))


class StripDiscountIdsTest(unittest.TestCase):
    def test_removes_nested_ids(self):
        discounts = [{
            '_id': 'a',
            'code': '[AUTO] VIP',
            'trigger': {
                '_id': 'b',
                'type': 'purchase',
                'purchased': [{'_id': 'c', 'ticketId': 't', 'quantity': 1}],
            },
        }]

        self.assertEqual(main.strip_discount_ids(discounts), [{
            'code': '[AUTO] VIP',
            'trigger': {
                'type': 'purchase',
                'purchased': [{'ticketId': 't', 'quantity': 1}],
            },
        }])

    def test_does_not_modify_input(self):
        discounts = [{'_id': 'a', 'code': '[AUTO] VIP'}]
        main.strip_discount_ids(discounts)

        self.assertEqual(discounts, [{'_id': 'a', 'code': '[AUTO] VIP'}])

    def test_tolerates_discounts_without_ids_or_trigger(self):
        self.assertEqual(
            main.strip_discount_ids([{'code': 'Host Guest'}]),
            [{'code': 'Host Guest'}],
        )

    def test_api_discount_matches_generated_discount(self):
        ticket_id = 't1'
        generated = list(main.generate_auto_discounts(VIP=ticket_id))
        from_api = main.strip_discount_ids(generated)
        for discount in from_api:
            discount['_id'] = 'x'
            discount['trigger']['_id'] = 'y'
            for purchased in discount['trigger']['purchased']:
                purchased['_id'] = 'z'

        self.assertEqual(main.strip_discount_ids(from_api), generated)


if __name__ == '__main__':
    unittest.main()
