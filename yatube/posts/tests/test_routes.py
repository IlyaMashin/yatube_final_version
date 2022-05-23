from django.test import TestCase
from django.urls import reverse

from ..urls import app_name

USERNAME = 'Vasya'
SLUG = 'test_slug'
POST_ID = '1'
URLS_LIST = [
    ['/', 'index', []],
    ['/create/', 'post_create', []],
    ['/follow/', 'follow_index', []],
    [f'/group/{SLUG}/', 'group_list', [SLUG]],
    [f'/profile/{USERNAME}/', 'profile', [USERNAME]],
    [f'/posts/{POST_ID}/edit/', 'post_edit', [POST_ID]],
    [f'/posts/{POST_ID}/', 'post_detail', [POST_ID]],
    [f'/posts/{POST_ID}/comment/', 'add_comment', [POST_ID]],
    [f'/profile/{USERNAME}/follow/', 'profile_follow', [USERNAME]],
    [f'/profile/{USERNAME}/unfollow/', 'profile_unfollow', [USERNAME]],
]


class PostRoutingTests(TestCase):

    def test_urls_correct_routing(self):
        for url, route, arg in URLS_LIST:
            with self.subTest(url=url, route=route):
                self.assertEqual(
                    url, reverse(f'{app_name}:{route}', args=arg)
                )
