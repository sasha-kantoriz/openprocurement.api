# -*- coding: utf-8 -*-
import unittest
from openprocurement.api.tests.base import test_tender_data, BaseWebTest


class TenderRevisionsTest(BaseWebTest):

    def setUp(self):
        super(TenderRevisionsTest, self).setUp()
        self.app.authorization = ('Basic', ('broker1h', ''))

    def test_rev_created(self):
        response = self.app.post_json('/tenders', {'data': test_tender_data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        tender = response.json['data']
        owner_token = response.json['access']['token']

        rev_db = self.db.get('r_{}'.format(tender['id']))
        self.assertTrue(rev_db is not None)
        self.assertEqual(len(rev_db['revisions']), 1)

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender['id'], owner_token), {'data': {'status': 'cancelled'}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertNotEqual(response.json['data']['status'], 'cancelled')
        self.assertEqual(rev_db, self.db.get('r_{}'.format(tender['id'])))

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender['id'], owner_token), {"data": {"guarantee": {"amount": 12}}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn('guarantee', response.json['data'])
        self.assertEqual(response.json['data']['guarantee']['amount'], 12)
        self.assertEqual(response.json['data']['guarantee']['currency'], 'UAH')

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender['id'], owner_token), {"data": {"guarantee": {"currency": "USD"}}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']['guarantee']['currency'], 'USD')

        rev_db = self.db.get('r_{}'.format(tender['id']))
        self.assertEqual(len(rev_db['revisions']), 3)
        self.assertEqual(rev_db['revisions'][-1]['changes'], [{u'path': u'/guarantee/currency', u'op': u'replace', u'value': u'UAH'}])

    def test_get_tender_versioned(self):
        response = self.app.post_json('/tenders', {'data': test_tender_data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.content_type, 'application/json')
        tender = response.json['data']
        tender.pop('dateModified')
        owner_token = response.json['access']['token']

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender['id'], owner_token), {"data": {"guarantee": {"amount": 12}}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn('guarantee', response.json['data'])
        self.assertEqual(response.json['data']['guarantee']['amount'], 12)
        self.assertEqual(response.json['data']['guarantee']['currency'], 'UAH')
        tender_v2 = response.json['data']
        tender_v2.pop('dateModified')

        response = self.app.patch_json('/tenders/{}?acc_token={}'.format(tender['id'], owner_token), {"data": {"guarantee": {"currency": "USD"}}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']['guarantee']['currency'], 'USD')
        tender_v3 = response.json['data']

        tender_last_v = self.app.get('/tenders/{}/historical'.format(tender['id']))
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(tender_v3, tender_last_v.json['data'])

        for v, t in enumerate([tender, tender_v2], 1):
            response = self.app.get('/tenders/{}/historical'.format(tender['id']),
                                    headers={'X-Revision-N': str(v)})
            self.assertEqual(response.status, '200 OK')
            self.assertEqual(response.content_type, 'application/json')
            tender_versioned = response.json['data']
            tender_versioned.pop('dateModified')
            self.assertEqual(t, tender_versioned)
