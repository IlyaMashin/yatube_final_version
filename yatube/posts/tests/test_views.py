import shutil
import tempfile

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from ..models import Post, Group, User, Follow

INDEX = reverse('posts:index')
POST_CREATE = reverse('posts:post_create')
AUTHOR = reverse('about:author')
TECH = reverse('about:tech')
AUTH_LOGIN = reverse('users:login')
USERNAME = 'auth'
GROUP_TITLE = 'test_group'
GROUP_SLUG = 'test_slug'
GROUP_DESCR = 'test_description'
TEST_TEXT = 'test_text'
GROUP_POSTS = reverse('posts:group_list', args=[GROUP_SLUG])
PROFILE = reverse('posts:profile', args=[USERNAME])
GROUP_TITLE_2 = 'test_group_2'
GROUP_SLUG_2 = 'test_slug_2'
GROUP_DESC_2 = 'test_description_2'
GROUP_POSTS_2 = reverse('posts:group_list', args=[GROUP_SLUG_2])
FOLLOW = reverse('posts:profile_follow', args=[USERNAME])
UNFOLLOW = reverse('posts:profile_unfollow', args=[USERNAME])
FOLLOW_INDEX = reverse('posts:follow_index')
TEST_IMAGE = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(dir=settings.BASE_DIR))
class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=TEST_IMAGE,
            content_type='image/gif'
        )
        cls.user = User.objects.create(username=USERNAME)
        cls.group = Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
            description=GROUP_DESCR,
        )
        cls.group_2 = Group.objects.create(
            title=GROUP_TITLE_2,
            slug=GROUP_SLUG_2,
            description=GROUP_DESC_2,
        )
        cls.post = Post.objects.create(
            text=TEST_TEXT,
            author=cls.user,
            group=cls.group,
            image=cls.uploaded,
        )
        cls.POST_DETAIL = reverse('posts:post_detail', args=[cls.post.pk])
        cls.POST_EDIT = reverse('posts:post_edit', args=[cls.post.pk])
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.user2 = User.objects.create(username='USERNAME2')
        cls.authorized_client2 = Client()
        cls.authorized_client2.force_login(cls.user2)
        cls.user3 = User.objects.create(username='USERNAME3')
        cls.authorized_client3 = Client()
        cls.authorized_client3.force_login(cls.user3)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_index_cache(self):
        "Тестирование cache на странице index.html"
        response = self.guest_client.get(INDEX)
        Post.objects.all().delete()
        response_after_delete_posts = self.guest_client.get(INDEX)
        cache.clear()
        response_after_cache_clean = self.guest_client.get(INDEX)
        self.assertEqual(
            response.content, response_after_delete_posts.content
        )
        self.assertNotEqual(response_after_cache_clean.content, response.content)

    def test_index_group_profile_correct_contexts(self):
        """
        Шаблоны index, group_list, profile, post_detail
        сформированы с правильным контекстом.
        """
        Follow.objects.get_or_create(user=self.user2, author=self.user)
        template_contexts = [
            [INDEX, self.guest_client, 'page_obj'],
            [GROUP_POSTS, self.guest_client, 'page_obj'],
            [PROFILE, self.guest_client, 'page_obj'],
            [self.POST_DETAIL, self.guest_client, 'post'],
            [FOLLOW_INDEX, self.authorized_client2, 'page_obj'],
        ]
        for url, client, object in template_contexts:
            with self.subTest(url=url):
                response = (client.get(url))
                if object == 'page_obj':
                    self.assertEqual((len(response.context[object])), 1)
                    post = response.context[object][0]
                else:
                    post = response.context[object]
                self.assertEqual(post.text, self.post.text)
                self.assertEqual(post.author, self.post.author)
                self.assertEqual(post.group, self.post.group)
                self.assertEqual(post.pk, self.post.pk)
                self.assertEqual(post.image, self.post.image)

    def test_post_in_other_place(self):
        """Пост не отображается в некорректном месте."""
        test_url = [
            [FOLLOW_INDEX, self.authorized_client],
            [GROUP_POSTS_2, self.authorized_client3],
        ]
        for url, client in test_url:
            with self.subTest(url=url):
                response = client.get(url)
                self.assertNotIn(self.post, response.context['page_obj'])

    def test_profile_page_show_correct_context(self):
        """Проверка отображения автора в контексте profile."""
        response = self.authorized_client.get(PROFILE)
        self.assertEqual(self.user, response.context.get('author'))

    def test_group_page_show_correct_context(self):
        """Проверка отображения группы в контексте group_list."""
        response = self.authorized_client.get(GROUP_POSTS)
        group = response.context.get('group')
        self.assertEqual(self.group.title, group.title)
        self.assertEqual(self.group.pk, group.pk)
        self.assertEqual(self.group.slug, group.slug)
        self.assertEqual(
            self.group.description, group.description
        )

    def test_follow_user(self):
        """Проверка подписки на автора """
        follow_exist = Follow.objects.get_or_create(user=self.user2,
                                             author=self.user)
        self.assertTrue(follow_exist)

    def test_unfollow_user(self):
        """Проверка отписки от автора """
        Follow.objects.get_or_create(user=self.user2, author=self.user)
        follow_count_before_delete = Follow.objects.count()
        Follow.objects.filter(user=self.user2, author=self.user).delete()
        self.assertEqual(Follow.objects.count(), follow_count_before_delete-1)

    def test_unfollow_index_posts_count(self):
        """Проверка страницы follow_index для неподписанного пользователя"""
        response = self.authorized_client3.get(FOLLOW_INDEX)
        self.assertEqual(len(response.context['page_obj']), 0)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username=USERNAME)
        cls.group = Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
            description=GROUP_DESCR,
        )
        Post.objects.bulk_create(Post(author=cls.user,
                                 group=cls.group,
                                 text=str(i)) for i in range(
                                     settings.POSTS_ON_PAGE + 3)
                                 )
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.user2 = User.objects.create(username='USERNAME2')
        cls.authorized_client2 = Client()
        cls.authorized_client2.force_login(cls.user2)

    def test_posts_on_page_count(self):
        Follow.objects.get_or_create(user=self.user2, author=self.user)
        posts_on_second_page = Post.objects.count() - settings.POSTS_ON_PAGE
        cases = [
            [INDEX, self.authorized_client, settings.POSTS_ON_PAGE],
            [f'{INDEX}?page=2', self.authorized_client, posts_on_second_page],
            [GROUP_POSTS, self.authorized_client, settings.POSTS_ON_PAGE],
            [f'{GROUP_POSTS}?page=2', self.authorized_client, posts_on_second_page],
            [PROFILE, self.authorized_client, settings.POSTS_ON_PAGE],
            [f'{PROFILE}?page=2', self.authorized_client, posts_on_second_page],
            [FOLLOW_INDEX, self.authorized_client2, settings.POSTS_ON_PAGE],
            [f'{FOLLOW_INDEX}?page=2', self.authorized_client2, posts_on_second_page],
        ]
        for url, client, posts_on_page in cases:
            with self.subTest(url=url):
                response = client.get(url)
                self.assertEqual(
                    len(response.context['page_obj']), posts_on_page
                )
