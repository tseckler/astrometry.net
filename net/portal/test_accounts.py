import unittest

from django.test.client import Client
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.core import mail

from astrometry.net.portal import accounts
from astrometry.net.portal.test_common import PortalTestCase
from astrometry.net.portal.models import UserProfile

class AccountTestCases(PortalTestCase):

    def setUp(self):
        super(AccountTestCases, self).setUp()
        self.url = reverse('astrometry.net.newaccount')

    def testFormValid(self):
        print 'Validating newaccount form:'
        self.validatePage(self.url)

    def testNewExistingAccount(self):
        print 'Users:'
        for u in User.objects.all():
            pro = UserProfile.for_user(u)
            print '  user', u, ', profile', pro

        resp = self.client.post(self.url, { 'email': self.u1 })
        self.assertEqual(resp.status_code, 200)
        #print 'Response:', resp
        ctxt = resp.context[0]
        #print 'Context:', ctxt
        form = ctxt['form']
        #print 'Form:', form
        self.assert_(not form.is_valid())
        #print 'errors:', form.errors
        self.assert_(form.errors)
        #print 'email error:', form.errors['email']
        self.assert_(form.errors['email'])
        self.assertEqual(form.errors['email'], ['That email address is already registered.',])

    def testNewAccount(self):
        e = 'newguy@astrometry.net'
        self.e = e
        resp = self.client.post(self.url, { 'email': e })
        self.assertEqual(resp.status_code, 200)
        #print 'Templates:', [t.name for t in resp.template]
        self.assertEqual(resp.template[0].name, 'portal/message.html')
        ctxt = resp.context[0]
        #print 'message:', ctxt['message']
        self.assertEqual(ctxt['message'], 'An email has been sent with instructions on how to activate your account.')

        # user was created.
        user = User.objects.get(username=e)
        self.assert_(user)
        self.assert_(user.get_profile())

        # activation_key was set...
        pro = user.get_profile()
        self.assert_(not pro.activated)
        key = pro.activation_key
        self.assert_(len(key) == 20)

        # an email was sent...
        self.assertEquals(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEquals(msg.subject, 'Your Astrometry.net account')
        self.assertEquals(msg.to, [e])
        self.assertEquals(msg.from_email, 'Astrometry.net Accounts <alpha@astrometry.net>')
        #print 'key is', key
        keyurl = self.urlprefix + reverse('astrometry.net.portal.accounts.activateaccount') + '?key=' + key
        print 'looking for key url', keyurl
        print 'msg body:', msg.body
        self.assert_(keyurl in msg.body)
        # save this url for the test below...
        #self.activation_url = keyurl
        self.key = key

        # user is authorized (in session)...?

    #def testNewPassword(self):

    def testNewAccountActivation(self):
        self.testNewAccount()
        resp = self.client.get(reverse('astrometry.net.portal.accounts.activateaccount'),
                               { 'key': self.key})
        print resp
        seturl = reverse('astrometry.net.setpassword')
        print 'seturl:', seturl
        self.assertRedirects(resp, seturl)
        pw = 'superSecret'

        # password mismatch
        resp = self.client.post(seturl, {'new_password1': pw,
                                         'new_password2': pw + 'bad'})
        self.assertNotContains(resp, "Password Set Successfully")
        ctxt = resp.context[0]
        form = ctxt['form']
        self.assert_(not form.is_valid())
        self.assert_(form.errors)

        # password match
        resp = self.client.post(seturl, {'new_password1': pw,
                                         'new_password2': pw})
        self.assertContains(resp, "Password Set Successfully")


        print self.client.session
        for k,v in self.client.session.items():
            print k,'=',v

        self.assert_(not self.client.session['allow_set_password'])

        user = User.objects.get(username=self.e)
        self.assert_(user)
        pro = user.get_profile()
        self.assert_(pro)
        self.assert_(pro.activated)
        self.assert_(not pro.activation_key)
