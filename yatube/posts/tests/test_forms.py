import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from ..models import Post, Group, User, Comment

USERNAME = 'auth'
AUTH_LOGIN = reverse('users:login')
GROUP_TITLE = 'test_group'
GROUP_SLUG = 'test_slug'
GROUP_DESCR = 'test_description'
TEST_TEXT = 'test_text'
COMMENT_TEXT = 'comment_text'
POST_CREATE = reverse('posts:post_create')
PROFILE = reverse('posts:profile', args=[USERNAME])
TEST_IMAGE_1 = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
)

@override_settings(MEDIA_ROOT=tempfile.mkdtemp(dir=settings.BASE_DIR))
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username=USERNAME)
        cls.group = Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
            description=GROUP_DESCR,
        )
        cls.group_2 = Group.objects.create(
            title='group_title',
            slug='group_slug',
            description='group_decr',
        )
        cls.post = Post.objects.create(
            text=TEST_TEXT,
            author=cls.user,
            group=cls.group,
        )
        cls.POST_DETAIL = reverse('posts:post_detail', args=[cls.post.pk])
        cls.POST_EDIT = reverse('posts:post_edit', args=[cls.post.pk])
        cls.ADD_COMMENT = reverse('posts:add_comment', args=[cls.post.pk])
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.user2 = User.objects.create(username="HasNoName")
        cls.authorized_client2 = Client()
        cls.authorized_client2.force_login(cls.user2)
        cls.uploaded_1 = SimpleUploadedFile(
            name='small.gif',
            content=TEST_IMAGE_1,
            content_type='image/gif'
        )
        cls.uploaded_2 = SimpleUploadedFile(
            name='little.gif',
            content=TEST_IMAGE_1,
            content_type='image/gif'
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_new_post_add(self):
        """Отправка валидной формы создает новую запись в базе"""
        Post.objects.all().delete()
        form_data = {
            'text': 'New_post',
            'group': self.group.pk,
            'image': self.uploaded_1,
        }
        response = self.authorized_client.post(
            POST_CREATE,
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), 1)
        post = Post.objects.first()
        dir_name = post._meta.get_field('image').upload_to
        self.assertRedirects(response, PROFILE)
        self.assertEqual(form_data['text'], post.text)
        self.assertEqual(form_data['group'], post.group.pk)
        self.assertEqual(f'{dir_name}{form_data["image"]}', post.image.name)
        self.assertEqual(self.user, post.author)

    def test_edit_post(self):
        """Проверка сохранения поста после редактирования"""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый пост отредактирован',
            'group': self.group_2.pk,
            'image': self.uploaded_2,
        }
        response = self.authorized_client.post(
            self.POST_EDIT,
            data=form_data,
            follow=True,
        )
        post = response.context['post']
        self.assertEqual(post_count, Post.objects.count())
        self.assertEqual(form_data['text'], post.text)
        self.assertEqual(form_data['group'], post.group.pk)
        self.assertEqual(f'posts/{form_data["image"]}', post.image)
        self.assertEqual(post.author, self.post.author)
        self.assertRedirects(response, self.POST_DETAIL)

    def test_guest_create_new_post(self):
        """Неавторизованный пользователь не может создать пост"""
        Post.objects.all().delete()
        form_data = {
            'text': 'New_post',
            'group': self.group.pk,
        }
        self.guest_client.post(
            POST_CREATE,
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), 0)

    def test_create_post_correct_contexts(self):
        """Шаблоны create/edit_post сформированы с правильным контекстом."""
        template_contexts = [
            [POST_CREATE, self.authorized_client],
            [self.POST_EDIT, self.authorized_client],
        ]
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for urls, client in template_contexts:
            with self.subTest(urls=urls):
                response = (client.get(urls))
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = (
                            response.context.get('form').fields.get(value)
                        )
                        self.assertIsInstance(form_field, expected)

    def test_guest_edit_post(self):
        """Неавторизованный пользователь не может редактировать пост."""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый пост отредактирован гостем',
            'group': self.group.pk,
        }
        self.guest_client.post(
            self.POST_EDIT,
            data=form_data,
            follow=True,
        )
        self.assertEqual(post_count, Post.objects.count())
        self.assertEqual(len(Post.objects.filter(text=form_data['text'])), 0)

    def test_not_author_edit_post(self):
        """Не автор не может редактировать пост."""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый пост отредактирован не автором',
            'group': self.group_2.pk,
        }
        self.authorized_client2.post(
            self.POST_EDIT,
            data=form_data,
            follow=True,
        )
        self.assertEqual(post_count, Post.objects.count())
        self.assertEqual(len(Post.objects.filter(text=form_data['text'])), 0)

class CommentFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username=USERNAME)
        cls.post = Post.objects.create(
            text=TEST_TEXT,
            author=cls.user,
        )
        cls.ADD_COMMENT = reverse('posts:add_comment', args=[cls.post.pk])
        cls.POST_DETAIL = reverse('posts:post_detail', args=[cls.post.pk])
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

    def test_create_new_comment(self):
        """Отправка валидной формы создает новый комментарий в базе"""
        Comment.objects.all().delete()
        form_data = {
            'text': COMMENT_TEXT,
        }
        response = self.authorized_client.post(
            self.ADD_COMMENT,
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.first()
        self.assertRedirects(response, self.POST_DETAIL)
        self.assertEqual(form_data['text'], comment.text)

    def test_guest_create_new_comment(self):
        """Неавторизованный пользователь не может оставлять комментарий"""
        Comment.objects.all().delete()
        form_data = {
            'text': COMMENT_TEXT,
        }
        self.guest_client.post(
            self.ADD_COMMENT,
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), 0)

    def test_new_comment_add(self):
        """Отправка валидной формы создает комментарий на странице поста."""
        Comment.objects.all().delete()
        form_data = {
            'text': COMMENT_TEXT,
            'author': self.user,
            'post': self.post,
        }
        self.authorized_client.post(
            self.ADD_COMMENT,
            data=form_data,
            follow=True
        )
        response = self.authorized_client.get(self.POST_DETAIL)
        self.assertEqual((len(response.context['comments'])), 1)
        comment = response.context['comments'][0]
        self.assertEqual(form_data['text'], comment.text)
        self.assertEqual(form_data['author'], comment.author)
        self.assertEqual(form_data['post'].pk, comment.post.pk)
