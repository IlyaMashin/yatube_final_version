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
GROUP_POSTS = reverse('posts:group_list', kwargs={'slug': GROUP_SLUG})
PROFILE = reverse('posts:profile', kwargs={'username': USERNAME})
GROUP_TITLE_2 = 'test_group_2'
GROUP_SLUG_2 = 'test_slug_2'
GROUP_DESC_2 = 'test_description_2'
GROUP_POSTS_2 = reverse('posts:group_list', kwargs={'slug': GROUP_SLUG_2})
FOLLOW = reverse('posts:profile_follow', kwargs={'username': USERNAME})
UNFOLLOW = reverse('posts:profile_unfollow', kwargs={'username': USERNAME})
FOLLOW_INDEX = reverse('posts:follow_index')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(dir=settings.BASE_DIR))
class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
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

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_index_cache(self):
        "Тестирование cache на странице index.html"
        cache.clear()
        response = self.guest_client.get(INDEX)
        Post.objects.all().delete()
        response_after_delete_posts = self.guest_client.get(INDEX)
        self.assertEqual(Post.objects.count(), 0)
        self.assertEqual(
            response.content, response_after_delete_posts.content
        )

    def test_index_group_profile_correct_contexts(self):
        """
        Шаблоны index, group_list, profile, post_detail
        сформированы с правильным контекстом.
        """
        self.authorized_client2.get(FOLLOW)
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

    def test_post_not_in_group2(self):
        """Пост не отображается в другой группе"""
        response = (self.authorized_client.get(GROUP_POSTS_2))
        self.assertNotIn(self.post, response.context.get('page_obj'))

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
        self.authorized_client2.get(FOLLOW)
        follow_exist = Follow.objects.filter(user=self.user2,
                                             author=self.user).exists()
        self.assertTrue(follow_exist)

    def test_unfollow_user(self):
        """Проверка отписки от автора """
        self.authorized_client2.get(FOLLOW)
        self.authorized_client2.get(UNFOLLOW)
        follow_exist = Follow.objects.filter(user=self.user2,
                                             author=self.user).exists()
        self.assertFalse(follow_exist)

    def test_follow_index_posts_count(self):
        """Проверка страницы follow_index для подписанного пользователя"""
        self.authorized_client2.get(FOLLOW)
        response = self.authorized_client2.get(FOLLOW_INDEX)
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertEqual(self.post, response.context.get('page_obj')[0])

    def test_unfollow_index_posts_count(self):
        """Проверка страницы follow_index для неподписанного пользователя"""
        response = self.authorized_client2.get(FOLLOW_INDEX)
        self.assertEqual(Post.objects.count(), 1)
        self.assertNotIn(self.post, response.context['page_obj'])


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

    def test_posts_on_page_count(self):
        posts_on_second_page = Post.objects.count() - settings.POSTS_ON_PAGE
        cases = [
            [INDEX, settings.POSTS_ON_PAGE],
            [f'{INDEX}?page=2', posts_on_second_page],
            [GROUP_POSTS, settings.POSTS_ON_PAGE],
            [f'{GROUP_POSTS}?page=2', posts_on_second_page],
            [PROFILE, settings.POSTS_ON_PAGE],
            [f'{PROFILE}?page=2', posts_on_second_page],
        ]
        for url, posts_on_page in cases:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(
                    len(response.context['page_obj']), posts_on_page
                )
