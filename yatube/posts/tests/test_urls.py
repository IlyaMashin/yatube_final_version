from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user

from ..models import Post, Group, User

INDEX = reverse('posts:index')
POST_CREATE = reverse('posts:post_create')
AUTH_LOGIN = reverse('users:login')
USERNAME = 'auth'
GROUP_TITLE = 'test_group'
GROUP_SLUG = 'test_slug'
GROUP_DESCR = 'test_description'
TEST_TEXT = 'test_text'
GROUP_POSTS = reverse('posts:group_list', args=[GROUP_SLUG])
PROFILE = reverse('posts:profile', args=[USERNAME])
FOLLOW_INDEX = reverse('posts:follow_index')
FOLLOW = reverse('posts:profile_follow', args=[USERNAME])
UNFOLLOW = reverse('posts:profile_unfollow', args=[USERNAME])
RANDOM_URL = '/qwerty/'


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username=USERNAME)
        cls.group = Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
            description=GROUP_DESCR,
        )
        cls.post = Post.objects.create(
            text=TEST_TEXT,
            author=cls.user,
            group=cls.group,
        )
        cls.POST_DETAIL = reverse('posts:post_detail', args=[cls.post.pk])
        cls.POST_EDIT = reverse('posts:post_edit', args=[cls.post.pk])
        cls.GUEST_CREATE_REDIRECT = f'{AUTH_LOGIN}?next={POST_CREATE}'
        cls.GUEST_EDIT_REDIRECT = f'{AUTH_LOGIN}?next={cls.POST_EDIT}'
        cls.GUEST_FOLLOW_INDEX = f'{AUTH_LOGIN}?next={FOLLOW_INDEX}'
        cls.GUEST_FOLLOW = f'{AUTH_LOGIN}?next={FOLLOW}'
        cls.GUEST_UNFOLLOW = f'{AUTH_LOGIN}?next={UNFOLLOW}'
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.user2 = User.objects.create(username="HasNoName")
        cls.authorized_client2 = Client()
        cls.authorized_client2.force_login(cls.user2)

    def test_posts_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        template_urls_names = [
            [INDEX, 'posts/index.html'],
            [FOLLOW_INDEX, 'posts/follow.html'],
            [POST_CREATE, 'posts/create_post.html'],
            [GROUP_POSTS, 'posts/group_list.html'],
            [self.POST_DETAIL, 'posts/post_detail.html'],
            [PROFILE, 'posts/profile.html'],
            [self.POST_EDIT, 'posts/create_post.html'],
        ]
        for url, template in template_urls_names:
            with self.subTest(url=url):
                self.assertTemplateUsed(self.authorized_client.get(url),
                                        template)

    def test_urls_status_code(self):
        """Проверка кода доступа пользователей к страницам"""
        urls_names = [
            [INDEX, self.guest_client, 200],
            [GROUP_POSTS, self.guest_client, 200],
            [PROFILE, self.guest_client, 200],
            [self.POST_DETAIL, self.guest_client, 200],
            [POST_CREATE, self.guest_client, 302],
            [RANDOM_URL, self.guest_client, 404],
            [POST_CREATE, self.authorized_client, 200],
            [self.POST_EDIT, self.authorized_client2, 302],
            [self.POST_EDIT, self.guest_client, 302],
            [self.POST_EDIT, self.authorized_client, 200],
            [FOLLOW_INDEX, self.authorized_client, 200],
            [FOLLOW_INDEX, self.guest_client, 302],
            [FOLLOW, self.authorized_client2, 302],
            [UNFOLLOW, self.authorized_client2, 302],
            [FOLLOW, self.guest_client, 302],
            [UNFOLLOW, self.guest_client, 302],
        ]
        for url, client, status, in urls_names:
            with self.subTest(
                url=url, client=get_user(client).username, status=status
            ):
                self.assertEqual(client.get(url).status_code, status)

    def test_correct_redirect(self):
        """Проверка редиректов"""
        urls = [
            [POST_CREATE, self.guest_client, self.GUEST_CREATE_REDIRECT],
            [self.POST_EDIT, self.guest_client, self.GUEST_EDIT_REDIRECT],
            [self.POST_EDIT, self.authorized_client2, self.POST_DETAIL],
            [FOLLOW_INDEX, self.guest_client, self.GUEST_FOLLOW_INDEX],
            [FOLLOW, self.authorized_client2, PROFILE],
            [UNFOLLOW, self.authorized_client2, PROFILE],
            [FOLLOW, self.guest_client, self.GUEST_FOLLOW],
            [UNFOLLOW, self.guest_client, self.GUEST_UNFOLLOW],
        ]
        for url, client, redirect in urls:
            with self.subTest(url=url, client=get_user(client).username):
                self.assertRedirects(client.get(url, follow=True), redirect)
