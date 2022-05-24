from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.conf import settings


from .forms import PostForm, CommentForm
from .models import Post, Group, User, Follow


def paginator_page(request, objects_list):
    return (
        Paginator(
            objects_list,
            settings.POSTS_ON_PAGE).get_page(request.GET.get('page'))
    )


def index(request):
    return render(request, 'posts/index.html', {
        'page_obj': paginator_page(request, Post.objects.all())
    })


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    return render(request, 'posts/group_list.html', {
        'group': group,
        'page_obj': paginator_page(request, group.posts.all()),
    })


def profile(request, username):
    user = get_object_or_404(User, username=username)
    following = request.user.is_authenticated and Follow.objects.filter(
        user=request.user, author=user).exists()
    return render(request, 'posts/profile.html', {
        'author': user,
        'following': following,
        'page_obj': paginator_page(request, user.posts.all()),
    })


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    context = {
        'post': post,
        'form': CommentForm(request.POST or None, files=request.FILES or None),
        'comments': paginator_page(request, post.comments.all()),
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if not form.is_valid():
        return render(request, 'posts/create_post.html', {'form': form})
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect('posts:profile', username=request.user)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if not form.is_valid():
        return render(request, 'posts/create_post.html', {
            'post': post,
            'form': form,
        })
    form.save()
    return redirect('posts:post_detail', post_id)


@login_required
def add_comment(request, post_id):
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = get_object_or_404(Post, pk=post_id)
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    follow_posts = Post.objects.filter(author__following__user=request.user)
    return render(
        request, 'posts/follow.html',
        {'page_obj': paginator_page(request, follow_posts)}
    )


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:profile', username=author.username)


@login_required
def profile_unfollow(request, username):
    (
        Follow.objects.filter(user=request.user, author__username=username)
    ).delete()
    return redirect('posts:profile', username=username)
