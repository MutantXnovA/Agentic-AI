import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from auth import hash_password, verify_password, generate_jwt, decode_jwt

class TestAuthRBAC(unittest.TestCase):

    def test_password_hashing_and_verification(self):
        pwd = 'SecurePassword@123'
        phash, salt = hash_password(pwd)
        self.assertTrue(verify_password(pwd, phash, salt))
        self.assertFalse(verify_password('WrongPassword', phash, salt))

    def test_jwt_generation_and_decoding(self):
        user_payload = {
            'id': 10,
            'username': 'testuser',
            'email': 'testuser@reconx.com',
            'role': 'reconciliation_analyst',
            'full_name': 'Test User'
        }
        token = generate_jwt(user_payload)
        decoded = decode_jwt(token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded['username'], 'testuser')
        self.assertEqual(decoded['role'], 'reconciliation_analyst')

if __name__ == '__main__':
    unittest.main()
