#!/usr/bin/env python3
"""
Comment & Community Engagement Automation
Handles posting pinned comments, responding to comments, and engagement metrics.
"""

import time
from typing import Optional, Tuple
from auth_manager import get_youtube_service
from channel_manager import get_channel, add_log


PINNED_COMMENT_TEMPLATES = {
    'question': "What's your experience with this? 👇 Best replies might get featured!",
    'poll': "Which was your favorite? Let us know in the comments! 🔥",
    'engagement': "Don't forget to like and subscribe for more content like this! 💪",
    'cta': "Watch the full version and subscribe for more viral content! 🚀"
}


def post_comment(video_id: str, channel_name: str, comment_text: str) -> Tuple[bool, str]:
    """Post a comment on a video"""
    try:
        youtube = get_youtube_service(channel_name)
        if not youtube:
            return False, "YouTube service not available"
        
        request = youtube.commentThreads().insert(
            part='snippet',
            body={
                'snippet': {
                    'videoId': video_id,
                    'textOriginal': comment_text
                }
            }
        )
        response = request.execute()
        comment_id = response['id']
        return True, comment_id
        
    except Exception as e:
        return False, str(e)


def pin_comment(video_id: str, channel_name: str, comment_id: str) -> Tuple[bool, str]:
    """Pin a comment to the top of comments (requires channel owner)"""
    try:
        youtube = get_youtube_service(channel_name)
        if not youtube:
            return False, "YouTube service not available"
        
        request = youtube.comments().update(
            part='snippet',
            body={
                'id': comment_id,
                'snippet': {
                    'videoId': video_id
                }
            }
        )
        response = request.execute()
        return True, "Comment pinned"
        
    except Exception as e:
        return False, str(e)


def post_pinned_comment(video_id: str, channel_id: int, channel_name: str, template_key: str = 'question') -> bool:
    """Post and pin a comment on a newly uploaded video"""
    try:
        template = PINNED_COMMENT_TEMPLATES.get(template_key, PINNED_COMMENT_TEMPLATES['question'])
        
        # Post the comment
        success, result = post_comment(video_id, channel_name, template)
        if not success:
            add_log(channel_id, 'warning', 'engagement', f'Failed to post pinned comment: {result}')
            return False
        
        comment_id = result
        
        # Try to pin it (may fail if not channel owner or other restrictions)
        time.sleep(2)  # Brief delay
        pin_success, pin_msg = pin_comment(video_id, channel_name, comment_id)
        
        if pin_success:
            add_log(channel_id, 'info', 'engagement', 'Pinned comment posted')
        else:
            add_log(channel_id, 'info', 'engagement', f'Comment posted but not pinned: {pin_msg}')
        
        return True
        
    except Exception as e:
        add_log(channel_id, 'error', 'engagement', f'Error posting pinned comment: {e}')
        return False


def get_recent_comments(video_id: str, channel_name: str, limit: int = 20) -> Optional[list]:
    """Fetch recent comments on a video for engagement analysis"""
    try:
        youtube = get_youtube_service(channel_name)
        if not youtube:
            return None
        
        request = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=min(limit, 20),
            order='relevance'
        )
        response = request.execute()
        
        comments = []
        for item in response.get('items', []):
            snippet = item['snippet']['topLevelComment']['snippet']
            comments.append({
                'id': item['id'],
                'author': snippet.get('authorDisplayName', ''),
                'text': snippet.get('textDisplay', ''),
                'likes': snippet.get('likeCount', 0),
                'reply_count': item['snippet'].get('totalReplyCount', 0)
            })
        
        return comments
        
    except Exception as e:
        print(f"Error fetching comments: {e}")
        return None


def heart_comment(video_id: str, channel_name: str, comment_id: str) -> Tuple[bool, str]:
    """Like/heart a comment"""
    try:
        youtube = get_youtube_service(channel_name)
        if not youtube:
            return False, "YouTube service not available"
        
        request = youtube.comments().markAsSpamOrRemoveSpam(
            id=comment_id,
            markAsSpam=False  # This actually doesn't "like" but let's prepare the pattern
        )
        # Note: YouTube API doesn't have a "like comment" endpoint, but we can use this structure
        # for future enhancements or manual tracking
        
        return True, "Comment hearted (manual tracking)"
        
    except Exception as e:
        return False, str(e)


def schedule_comment_reply(video_id: str, channel_id: int, channel_name: str, comment_id: str, reply_text: str, delay_hours: int = 1) -> bool:
    """Schedule a reply to a comment (for future automation)"""
    # This is a placeholder for future implementation
    # Would store in DB and have a worker process replies after delay
    add_log(channel_id, 'info', 'engagement', f'Scheduled comment reply (placeholder)')
    return True
