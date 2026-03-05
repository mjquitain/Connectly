from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token
from rest_framework import status
from .models import Post, Comment, Like


# ---------------------------------------------------------------------------
# Singleton / Config Tests (kept from original)
# ---------------------------------------------------------------------------

class ConfigTest(TestCase):
    def test_singleton_behavior(self):
        from singletons.config_manager import ConfigManager
        config1 = ConfigManager()
        config2 = ConfigManager()
        assert config1 is config2
        config1.set_setting("DEFAULT_PAGE_SIZE", 50)
        assert config2.get_setting("DEFAULT_PAGE_SIZE") == 50


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username='testuser', password='TestPass123!'):
    user = User.objects.create_user(username=username, password=password, email=f'{username}@example.com')
    token, _ = Token.objects.get_or_create(user=user)
    return user, token


def make_post(author, post_type='text', title='Hello', content='World'):
    return Post.objects.create(author=author, post_type=post_type, title=title, content=content)


# ---------------------------------------------------------------------------
# Like Tests
# ---------------------------------------------------------------------------

class LikePostTests(APITestCase):
    def setUp(self):
        self.user, self.token = make_user('liker')
        self.other, self.other_token = make_user('other')
        self.post = make_post(self.other)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def url(self, pk=None):
        return f'/posts/posts/{pk or self.post.id}/like/'

    def test_like_post_returns_201(self):
        response = self.client.post(self.url())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['like_count'], 1)
        self.assertTrue(response.data['liked_by_me'])

    def test_like_increments_count(self):
        self.client.post(self.url())
        self.assertEqual(Like.objects.filter(post=self.post).count(), 1)

    def test_unlike_toggles_off(self):
        # First like
        self.client.post(self.url())
        # Second POST on same post → unlike
        response = self.client.post(self.url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['like_count'], 0)
        self.assertFalse(response.data['liked_by_me'])

    def test_cannot_double_like(self):
        """After unlike toggle, count should be 0 — no duplicate rows allowed."""
        self.client.post(self.url())
        self.client.post(self.url())  # unlike
        self.client.post(self.url())  # like again
        self.assertEqual(Like.objects.filter(post=self.post).count(), 1)

    def test_get_like_status_unauthenticated(self):
        self.client.credentials()
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_like_status_authenticated(self):
        self.client.post(self.url())
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['like_count'], 1)
        self.assertTrue(response.data['liked_by_me'])

    def test_like_nonexistent_post(self):
        response = self.client.post(self.url(pk=9999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_multiple_users_can_like_same_post(self):
        self.client.post(self.url())
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        self.client.post(self.url())
        self.assertEqual(Like.objects.filter(post=self.post).count(), 2)


# ---------------------------------------------------------------------------
# Post-scoped Comment Tests
# ---------------------------------------------------------------------------

class PostCommentTests(APITestCase):
    def setUp(self):
        self.author, self.token = make_user('commenter')
        self.other, self.other_token = make_user('poster')
        self.post = make_post(self.other)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def list_url(self, pk=None):
        return f'/posts/posts/{pk or self.post.id}/comments/'

    def test_create_comment_returns_201(self):
        response = self.client.post(self.list_url(), {'text': 'Great post!'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['text'], 'Great post!')

    def test_comment_author_set_from_token(self):
        self.client.post(self.list_url(), {'text': 'Nice'})
        comment = Comment.objects.get(post=self.post)
        self.assertEqual(comment.author, self.author)

    def test_empty_comment_rejected(self):
        response = self.client.post(self.list_url(), {'text': ''})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_whitespace_only_comment_rejected(self):
        response = self.client.post(self.list_url(), {'text': '   '})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_text_rejected(self):
        response = self.client.post(self.list_url(), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_comments_for_post(self):
        Comment.objects.create(author=self.author, post=self.post, text='First')
        Comment.objects.create(author=self.other, post=self.post, text='Second')
        response = self.client.get(self.list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['comment_count'], 2)
        self.assertEqual(len(response.data['comments']), 2)

    def test_get_comments_returns_only_that_posts_comments(self):
        other_post = make_post(self.other, title='Other Post')
        Comment.objects.create(author=self.author, post=self.post, text='On post 1')
        Comment.objects.create(author=self.author, post=other_post, text='On post 2')
        response = self.client.get(self.list_url())
        self.assertEqual(response.data['comment_count'], 1)

    def test_comment_on_nonexistent_post(self):
        response = self.client.post(self.list_url(pk=9999), {'text': 'Hello?'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_cannot_comment(self):
        self.client.credentials()
        response = self.client.post(self.list_url(), {'text': 'No auth'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_cannot_list_comments(self):
        self.client.credentials()
        response = self.client.get(self.list_url())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_comments_ordered_by_created_at(self):
        Comment.objects.create(author=self.author, post=self.post, text='Alpha')
        Comment.objects.create(author=self.author, post=self.post, text='Beta')
        response = self.client.get(self.list_url())
        texts = [c['text'] for c in response.data['comments']]
        self.assertEqual(texts, ['Alpha', 'Beta'])


# ---------------------------------------------------------------------------
# Post Serializer — like_count / comment_count
# ---------------------------------------------------------------------------

class PostSerializerCountTests(APITestCase):
    def setUp(self):
        self.user, self.token = make_user('counter')
        self.post = make_post(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_post_includes_like_count(self):
        Like.objects.create(user=self.user, post=self.post)
        response = self.client.get(f'/posts/posts/{self.post.id}/')
        self.assertEqual(response.data['like_count'], 1)

    def test_post_includes_comment_count(self):
        Comment.objects.create(author=self.user, post=self.post, text='Hi')
        response = self.client.get(f'/posts/posts/{self.post.id}/')
        self.assertEqual(response.data['comment_count'], 1)


# ---------------------------------------------------------------------------
# Google OAuth Tests
# ---------------------------------------------------------------------------

from unittest.mock import patch, MagicMock
from .models import GoogleSocialAccount


def make_google_payload(sub='google-uid-123', email='googleuser@gmail.com',
                         name='Google User', picture='https://pic.google.com/photo.jpg'):
    """Return a realistic mock payload as returned by verify_google_token()."""
    return {
        'sub':            sub,
        'email':          email,
        'email_verified': 'true',
        'name':           name,
        'given_name':     name.split()[0],
        'family_name':    name.split()[-1],
        'picture':        picture,
        'aud':            'test-client-id.apps.googleusercontent.com',
    }


GOOGLE_VERIFY_PATH = 'posts.views.verify_google_token'
GOOGLE_LOGIN_URL   = '/posts/auth/google/login/'


class GoogleLoginNewUserTests(APITestCase):
    """Scenario 3 — brand-new user: no matching google_id or email exists."""

    @patch(GOOGLE_VERIFY_PATH)
    def test_new_user_returns_201(self, mock_verify):
        mock_verify.return_value = make_google_payload()
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch(GOOGLE_VERIFY_PATH)
    def test_new_user_created_flag_is_true(self, mock_verify):
        mock_verify.return_value = make_google_payload()
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.assertTrue(response.data['created'])

    @patch(GOOGLE_VERIFY_PATH)
    def test_new_user_token_returned(self, mock_verify):
        mock_verify.return_value = make_google_payload()
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.assertIn('token', response.data)
        self.assertTrue(len(response.data['token']) > 10)

    @patch(GOOGLE_VERIFY_PATH)
    def test_new_user_django_user_created(self, mock_verify):
        mock_verify.return_value = make_google_payload(email='newperson@gmail.com')
        self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.assertTrue(User.objects.filter(email='newperson@gmail.com').exists())

    @patch(GOOGLE_VERIFY_PATH)
    def test_new_user_google_social_account_created(self, mock_verify):
        payload = make_google_payload(sub='unique-sub-001')
        mock_verify.return_value = payload
        self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.assertTrue(GoogleSocialAccount.objects.filter(google_id='unique-sub-001').exists())

    @patch(GOOGLE_VERIFY_PATH)
    def test_new_user_has_no_password(self, mock_verify):
        mock_verify.return_value = make_google_payload(email='nopass@gmail.com')
        self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        user = User.objects.get(email='nopass@gmail.com')
        self.assertFalse(user.has_usable_password())

    @patch(GOOGLE_VERIFY_PATH)
    def test_username_derived_from_email_prefix(self, mock_verify):
        mock_verify.return_value = make_google_payload(email='johndoe@gmail.com')
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.assertEqual(response.data['user']['username'], 'johndoe')

    @patch(GOOGLE_VERIFY_PATH)
    def test_duplicate_username_gets_suffix(self, mock_verify):
        # Pre-create a user with the derived username
        User.objects.create_user(username='johndoe', email='other@example.com', password='x')
        mock_verify.return_value = make_google_payload(email='johndoe@gmail.com', sub='sub-999')
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        # Should get johndoe1 since johndoe is taken
        self.assertEqual(response.data['user']['username'], 'johndoe1')

    @patch(GOOGLE_VERIFY_PATH)
    def test_new_user_message_correct(self, mock_verify):
        mock_verify.return_value = make_google_payload()
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.assertIn('New Connectly account created', response.data['message'])


class GoogleLoginReturningUserTests(APITestCase):
    """Scenario 1 — returning user: GoogleSocialAccount already exists."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='existinguser', email='existing@gmail.com', password=None
        )
        self.social = GoogleSocialAccount.objects.create(
            user=self.user,
            google_id='returning-sub-456',
            email='existing@gmail.com',
            name='Existing User',
        )

    @patch(GOOGLE_VERIFY_PATH)
    def test_returning_user_returns_200(self, mock_verify):
        mock_verify.return_value = make_google_payload(
            sub='returning-sub-456', email='existing@gmail.com'
        )
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_VERIFY_PATH)
    def test_returning_user_created_flag_is_false(self, mock_verify):
        mock_verify.return_value = make_google_payload(sub='returning-sub-456')
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.assertFalse(response.data['created'])

    @patch(GOOGLE_VERIFY_PATH)
    def test_returning_user_no_duplicate_created(self, mock_verify):
        mock_verify.return_value = make_google_payload(sub='returning-sub-456')
        self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        # Still only one GoogleSocialAccount
        self.assertEqual(GoogleSocialAccount.objects.filter(google_id='returning-sub-456').count(), 1)

    @patch(GOOGLE_VERIFY_PATH)
    def test_returning_user_profile_updated(self, mock_verify):
        mock_verify.return_value = make_google_payload(
            sub='returning-sub-456', name='Updated Name'
        )
        self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.social.refresh_from_db()
        self.assertEqual(self.social.name, 'Updated Name')

    @patch(GOOGLE_VERIFY_PATH)
    def test_returning_user_message_correct(self, mock_verify):
        mock_verify.return_value = make_google_payload(sub='returning-sub-456')
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.assertIn('Logged in with Google successfully', response.data['message'])


class GoogleLoginEmailLinkingTests(APITestCase):
    """Scenario 2 — email match: existing User with same email, no GoogleSocialAccount yet."""

    def setUp(self):
        self.user, self.token = make_user('manual_user', 'StrongPass123!')
        # Override email to match what Google will return
        self.user.email = 'manual@gmail.com'
        self.user.save()

    @patch(GOOGLE_VERIFY_PATH)
    def test_linking_returns_200(self, mock_verify):
        mock_verify.return_value = make_google_payload(
            sub='link-sub-789', email='manual@gmail.com'
        )
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(GOOGLE_VERIFY_PATH)
    def test_linking_preserves_original_username(self, mock_verify):
        mock_verify.return_value = make_google_payload(
            sub='link-sub-789', email='manual@gmail.com'
        )
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.assertEqual(response.data['user']['username'], 'manual_user')

    @patch(GOOGLE_VERIFY_PATH)
    def test_linking_creates_google_social_account(self, mock_verify):
        mock_verify.return_value = make_google_payload(
            sub='link-sub-789', email='manual@gmail.com'
        )
        self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.assertTrue(
            GoogleSocialAccount.objects.filter(user=self.user, google_id='link-sub-789').exists()
        )

    @patch(GOOGLE_VERIFY_PATH)
    def test_linking_message_correct(self, mock_verify):
        mock_verify.return_value = make_google_payload(
            sub='link-sub-789', email='manual@gmail.com'
        )
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.assertIn('linked to your existing Connectly account', response.data['message'])

    @patch(GOOGLE_VERIFY_PATH)
    def test_linked_user_created_flag_is_false(self, mock_verify):
        mock_verify.return_value = make_google_payload(
            sub='link-sub-789', email='manual@gmail.com'
        )
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        self.assertFalse(response.data['created'])


class GoogleLoginErrorTests(APITestCase):
    """Error cases and edge cases for the Google OAuth endpoint."""

    def test_missing_id_token_field(self):
        response = self.client.post(GOOGLE_LOGIN_URL, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('id_token is required', response.data['error'])

    def test_null_id_token(self):
        """Null is treated as missing by DRF CharField — triggers 'required' error."""
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': None}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('id_token is required', response.data['error'])

    def test_blank_string_id_token(self):
        """Empty string passes 'required' but is caught by validate_id_token."""
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': ''}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'id_token must not be blank.')

    def test_whitespace_only_id_token(self):
        """Whitespace-only string is treated as blank by validate_id_token."""
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': '   '}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'id_token must not be blank.')

    @patch(GOOGLE_VERIFY_PATH)
    def test_invalid_token_returns_400(self, mock_verify):
        from posts.google_auth import GoogleAuthError
        mock_verify.side_effect = GoogleAuthError('Google rejected the token: {"error":"invalid_token"}')
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'bad.token'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Google rejected the token', response.data['error'])

    @patch(GOOGLE_VERIFY_PATH)
    def test_expired_token_returns_400(self, mock_verify):
        from posts.google_auth import GoogleAuthError
        mock_verify.side_effect = GoogleAuthError('Google rejected the token: {"error":"invalid_token","error_description":"Token expired or revoked"}')
        response = self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'expired.token'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_google_only_user_cannot_use_password_login(self):
        """User created via Google (no password) cannot log in via /login/."""
        User.objects.create_user(username='googleonly', email='g@gmail.com', password=None)
        response = self.client.post(
            '/posts/login/',
            {'username': 'googleonly', 'password': 'anything'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(GOOGLE_VERIFY_PATH)
    def test_google_token_works_on_protected_endpoint(self, mock_verify):
        """Token from Google login must work on all protected endpoints."""
        mock_verify.return_value = make_google_payload(sub='access-sub-111', email='access@gmail.com')
        login_resp = self.client.post(GOOGLE_LOGIN_URL, {'id_token': 'fake.token'}, format='json')
        token = login_resp.data['token']

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        response = self.client.get('/posts/posts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_auth_header_on_regular_endpoint_returns_401(self):
        """Sanity check — protected endpoints still require auth."""
        self.client.credentials()
        response = self.client.get('/posts/posts/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)