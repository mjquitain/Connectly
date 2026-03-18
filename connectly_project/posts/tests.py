from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ConnectlyUser, Post, Comment
from singletons.config_manager import ConfigManager

# Create your tests here.
class ConfigTest(TestCase):
    def test_singleton_behavior(self):
    
#     def tearDown(self):
#         if hasattr(config_manager, '_reset'):
#             config_manager._reset()
            
#     @override_settings(MY_APP_CONFIG='test_key')
#     def test_custom_config(self):
        
#         self.assertEqual(get_config(), 'test_key')
        
#     @override_settings(MY_APP_CONFIG='new_test')
#     def test_config_change(self):
        
#         self.assertEqual(get_config(), 'new_test')
        
        config1 = ConfigManager()
        config2 = ConfigManager()

        assert config1 is config2
        config1.set_setting("DEFAULT_PAGE_SIZE", 50)
        assert config2.get_setting("DEFAULT_PAGE_SIZE") == 50


class APIRbacAndPrivacyTests(APITestCase):
    def setUp(self):
        cache.clear()

        self.admin_django_user, self.admin_connectly_user = self._create_user_pair(
            username='admin_user',
            email='admin@example.com',
            role='admin'
        )
        self.owner_django_user, self.owner_connectly_user = self._create_user_pair(
            username='owner_user',
            email='owner@example.com',
            role='user'
        )
        self.other_django_user, self.other_connectly_user = self._create_user_pair(
            username='other_user',
            email='other@example.com',
            role='user'
        )

        self.admin_token = Token.objects.create(user=self.admin_django_user)
        self.owner_token = Token.objects.create(user=self.owner_django_user)
        self.other_token = Token.objects.create(user=self.other_django_user)

        self.public_post = Post.objects.create(
            author=self.owner_connectly_user,
            title='Public post',
            content='Visible to everyone',
            post_type='text',
            privacy='public',
            metadata={}
        )
        self.private_post = Post.objects.create(
            author=self.owner_connectly_user,
            title='Private post',
            content='Visible only to owner',
            post_type='text',
            privacy='private',
            metadata={}
        )

        self.comment = Comment.objects.create(
            author=self.owner_connectly_user,
            post=self.public_post,
            text='Owner comment'
        )

    def _create_user_pair(self, username, email, role='user'):
        django_user = User.objects.create_user(
            username=username,
            email=email,
            password='StrongPass123!'
        )
        connectly_user = ConnectlyUser.objects.create(
            username=username,
            email=email,
            role=role
        )
        return django_user, connectly_user

    def _auth_with_token(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_admin_can_delete_post_success(self):
        self._auth_with_token(self.admin_token)

        response = self.client.delete(
            reverse('post-detail', kwargs={'pk': self.public_post.id})
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Post.objects.filter(id=self.public_post.id).exists())

    def test_non_admin_cannot_delete_post_forbidden(self):
        self._auth_with_token(self.other_token)

        response = self.client.delete(
            reverse('post-detail', kwargs={'pk': self.public_post.id})
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Post.objects.filter(id=self.public_post.id).exists())

    def test_owner_can_view_private_post_success(self):
        self._auth_with_token(self.owner_token)

        response = self.client.get(
            reverse('post-detail', kwargs={'pk': self.private_post.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.private_post.id)

    def test_other_user_cannot_view_private_post_forbidden(self):
        self._auth_with_token(self.other_token)

        response = self.client.get(
            reverse('post-detail', kwargs={'pk': self.private_post.id})
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_feed_shows_public_and_own_private_posts_only(self):
        self._auth_with_token(self.owner_token)
        owner_feed_response = self.client.get(reverse('news-feed'))
        owner_ids = {item['id'] for item in owner_feed_response.data['results']}

        self.assertEqual(owner_feed_response.status_code, status.HTTP_200_OK)
        self.assertIn(self.public_post.id, owner_ids)
        self.assertIn(self.private_post.id, owner_ids)

        self._auth_with_token(self.other_token)
        other_feed_response = self.client.get(reverse('news-feed'))
        other_ids = {item['id'] for item in other_feed_response.data['results']}

        self.assertEqual(other_feed_response.status_code, status.HTTP_200_OK)
        self.assertIn(self.public_post.id, other_ids)
        self.assertNotIn(self.private_post.id, other_ids)

    def test_unauthenticated_user_cannot_access_protected_resources(self):
        self.client.credentials()

        post_response = self.client.get(
            reverse('post-detail', kwargs={'pk': self.public_post.id})
        )
        feed_response = self.client.get(reverse('news-feed'))

        self.assertEqual(post_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(feed_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_delete_comment_success(self):
        self._auth_with_token(self.admin_token)

        response = self.client.delete(
            reverse('comment-detail', kwargs={'pk': self.comment.id})
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(id=self.comment.id).exists())

    def test_non_admin_cannot_delete_comment_forbidden(self):
        self._auth_with_token(self.other_token)

        response = self.client.delete(
            reverse('comment-detail', kwargs={'pk': self.comment.id})
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Comment.objects.filter(id=self.comment.id).exists())

    def test_staff_user_without_connectly_profile_can_delete_comment(self):
        staff_user = User.objects.create_user(
            username='staff_only_admin',
            email='staff@example.com',
            password='StrongPass123!',
            is_staff=True
        )
        staff_token = Token.objects.create(user=staff_user)
        self._auth_with_token(staff_token)

        response = self.client.delete(
            reverse('comment-detail', kwargs={'pk': self.comment.id})
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(id=self.comment.id).exists())

    def test_create_comment_returns_comment_id(self):
        self._auth_with_token(self.owner_token)

        response = self.client.post(
            reverse('post-comment', kwargs={'pk': self.public_post.id}),
            data={'text': 'New comment from owner'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('comment', response.data)
        self.assertIn('id', response.data['comment'])
        self.assertEqual(response.data['comment']['post_id'], self.public_post.id)

    def test_admin_can_delete_comment_by_post_and_comment_ids(self):
        self._auth_with_token(self.admin_token)

        response = self.client.delete(
            reverse(
                'post-comment-detail',
                kwargs={'post_pk': self.public_post.id, 'comment_pk': self.comment.id}
            )
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(id=self.comment.id).exists())

    def test_feed_respects_page_size_limit(self):
        for i in range(15):
            Post.objects.create(
                author=self.owner_connectly_user,
                title=f'Public post {i}',
                content='bulk',
                post_type='text',
                privacy='public',
                metadata={}
            )

        self._auth_with_token(self.other_token)
        response = self.client.get(reverse('news-feed'), {'page': 1, 'page_size': 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)

    def test_feed_uses_cache_for_same_user_and_page(self):
        self._auth_with_token(self.other_token)
        first_response = self.client.get(reverse('news-feed'), {'page': 1, 'page_size': 10})
        first_count = first_response.data['count']

        self._auth_with_token(self.owner_token)
        create_response = self.client.post(
            reverse('post-list-create'),
            data={
                'title': 'Fresh public post',
                'content': 'new',
                'post_type': 'text',
                'privacy': 'public',
                'metadata': {}
            },
            format='json'
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        self._auth_with_token(self.other_token)
        second_response = self.client.get(reverse('news-feed'), {'page': 1, 'page_size': 10})
        second_count = second_response.data['count']

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        # New post write bumps feed cache version, so count should refresh.
        self.assertGreater(second_count, first_count)