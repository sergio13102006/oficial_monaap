from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import AuthSecurityEvent, AuthSecurityState


LOGIN_USER_BLOCK_LEVELS = (
    (5, timedelta(minutes=1)),
    (8, timedelta(minutes=5)),
    (12, timedelta(minutes=15)),
    (16, timedelta(minutes=30)),
)
LOGIN_CAPTCHA_THRESHOLD = 4
LOGIN_IP_BURST_THRESHOLD = 5
LOGIN_IP_BURST_WINDOW = timedelta(seconds=60)
LOGIN_IP_BURST_BLOCK = timedelta(minutes=15)
LOGIN_IP_SUSPICIOUS_WINDOW = timedelta(hours=24)
LOGIN_REPUTATION_WINDOW = timedelta(days=7)
LOGIN_STRONG_BLOCK = timedelta(days=7)
LOGIN_RECOVERY_MAX_REQUESTS = 5
LOGIN_RECOVERY_WINDOW = timedelta(hours=1)


@dataclass
class LoginDecision:
    blocked: bool
    blocked_until: object | None
    blocked_minutes: int
    captcha_required: bool
    user_state: AuthSecurityState | None
    ip_state: AuthSecurityState | None


def normalize_subject(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    return normalized or "anon"


def get_client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "0.0.0.0")
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def get_user_agent(request) -> str:
    return (request.META.get("HTTP_USER_AGENT") or "").strip()[:255]


def get_security_state(subject_type: str, subject_value: str) -> AuthSecurityState:
    state, _ = AuthSecurityState.objects.get_or_create(
        subject_type=subject_type,
        subject_value=subject_value,
    )
    return state


def _state_active_until(state: AuthSecurityState | None, now):
    if not state:
        return None
    candidates = [
        state.blocked_until,
        state.strong_block_until,
        state.burst_block_until,
    ]
    valid = [value for value in candidates if value and value > now]
    return max(valid, default=None)


def _captcha_required_for_state(state: AuthSecurityState | None, now) -> bool:
    if not state:
        return False
    if state.captcha_required_until and state.captcha_required_until > now:
        return True
    return state.failed_count >= LOGIN_CAPTCHA_THRESHOLD - 1


def _block_duration_for_user_failures(failed_count: int):
    if failed_count >= 16:
        return LOGIN_USER_BLOCK_LEVELS[3][1]
    if failed_count >= 12:
        return LOGIN_USER_BLOCK_LEVELS[2][1]
    if failed_count >= 8:
        return LOGIN_USER_BLOCK_LEVELS[1][1]
    if failed_count >= 5:
        return LOGIN_USER_BLOCK_LEVELS[0][1]
    return None


def _active_block_candidates(*states, now):
    candidates = []
    for state in states:
        until = _state_active_until(state, now)
        if until:
            candidates.append(until)
    return max(candidates, default=None)


def _reset_user_login_state(state: AuthSecurityState, now):
    state.failed_count = 0
    state.block_level = 0
    state.blocked_until = None
    state.strong_block_until = None
    state.captcha_required_until = None
    state.last_success_at = now
    state.last_failed_at = None
    state.save(update_fields=[
        "failed_count",
        "block_level",
        "blocked_until",
        "strong_block_until",
        "captcha_required_until",
        "last_success_at",
        "last_failed_at",
        "updated_at",
    ])


def _soften_ip_state_on_success(state: AuthSecurityState, now):
    state.failed_count = 0
    state.burst_count = 0
    state.burst_strikes = 0
    state.burst_window_started_at = None
    state.burst_block_until = None
    state.suspicious_until = None
    state.reputation_score = 0
    state.reputation_expires_at = None
    state.last_burst_at = None
    state.strong_block_until = None
    state.captcha_required_until = None
    state.last_failed_at = None
    state.last_success_at = now
    state.save(update_fields=[
        "failed_count",
        "burst_count",
        "burst_strikes",
        "burst_window_started_at",
        "burst_block_until",
        "suspicious_until",
        "reputation_score",
        "reputation_expires_at",
        "last_burst_at",
        "strong_block_until",
        "captcha_required_until",
        "last_failed_at",
        "last_success_at",
        "updated_at",
    ])


def _update_reputation(state: AuthSecurityState, now, burst_hit=False):
    previous_burst_at = state.last_burst_at

    if state.reputation_expires_at and state.reputation_expires_at <= now:
        state.reputation_score = 0

    if burst_hit:
        state.reputation_score += 1
        if previous_burst_at and (now - previous_burst_at) <= LOGIN_IP_BURST_WINDOW:
            state.burst_strikes += 1
        else:
            state.burst_strikes = 1
        state.last_burst_at = now

    state.reputation_expires_at = now + LOGIN_REPUTATION_WINDOW

    if state.reputation_score >= 6 or state.burst_strikes >= 3:
        state.strong_block_until = now + LOGIN_STRONG_BLOCK


def register_login_attempt(
    *,
    request,
    username: str,
    success: bool,
    event_type: str,
    details: dict | None = None,
    user=None,
    subject_type: str = AuthSecurityState.SUBJECT_USER,
    subject_value: str | None = None,
):
    ip = get_client_ip(request)
    AuthSecurityEvent.objects.create(
        event_type=event_type,
        subject_type=subject_type,
        subject_value=subject_value if subject_value is not None else normalize_subject(username),
        user=user,
        username=username or "",
        ip_address=ip,
        user_agent=get_user_agent(request),
        success=success,
        details=details or {},
    )


def evaluate_login_gate(request, username: str, now=None) -> LoginDecision:
    now = now or timezone.now()
    ip = get_client_ip(request)
    user_state = get_security_state(AuthSecurityState.SUBJECT_USER, normalize_subject(username))
    ip_state = get_security_state(AuthSecurityState.SUBJECT_IP, ip)
    blocked_until = _active_block_candidates(user_state, ip_state, now=now)
    captcha_required = _captcha_required_for_state(user_state, now) or _captcha_required_for_state(ip_state, now)
    if ip_state.suspicious_until and ip_state.suspicious_until > now:
        captcha_required = True

    blocked_minutes = 0
    if blocked_until and blocked_until > now:
        blocked_minutes = int((blocked_until - now).total_seconds() // 60) or 1

    return LoginDecision(
        blocked=bool(blocked_until and blocked_until > now),
        blocked_until=blocked_until,
        blocked_minutes=blocked_minutes,
        captcha_required=captcha_required,
        user_state=user_state,
        ip_state=ip_state,
    )


def validate_recaptcha(token: str | None, remote_ip: str | None = None) -> bool:
    site_key = getattr(settings, "LOGIN_RECAPTCHA_SITE_KEY", "")
    secret_key = getattr(settings, "LOGIN_RECAPTCHA_SECRET_KEY", "")

    if not site_key or not secret_key:
        return True

    if not token:
        return False

    payload = {
        "secret": secret_key,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://www.google.com/recaptcha/api/siteverify",
        data=data,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return False

    return bool(result.get("success"))


def register_login_failure(
    *,
    request,
    username: str,
    user_state: AuthSecurityState,
    ip_state: AuthSecurityState,
    reason: str,
    captcha_used: bool = False,
):
    now = timezone.now()

    user_state.failed_count += 1
    user_state.last_failed_at = now
    user_state.captcha_required_until = now + LOGIN_IP_SUSPICIOUS_WINDOW if user_state.failed_count >= LOGIN_CAPTCHA_THRESHOLD else user_state.captcha_required_until

    user_block_duration = _block_duration_for_user_failures(user_state.failed_count)
    if user_block_duration:
        user_state.block_level = {
            timedelta(minutes=1): 1,
            timedelta(minutes=5): 2,
            timedelta(minutes=15): 3,
            timedelta(minutes=30): 4,
        }.get(user_block_duration, user_state.block_level or 1)
        user_state.blocked_until = now + user_block_duration
    if user_state.failed_count >= 20:
        user_state.strong_block_until = now + LOGIN_STRONG_BLOCK

    ip_state.failed_count += 1
    ip_state.last_failed_at = now

    if not ip_state.burst_window_started_at or (now - ip_state.burst_window_started_at) > LOGIN_IP_BURST_WINDOW:
        ip_state.burst_window_started_at = now
        ip_state.burst_count = 1
    else:
        ip_state.burst_count += 1

    burst_hit = False
    if ip_state.burst_count >= LOGIN_IP_BURST_THRESHOLD:
        burst_hit = True
        ip_state.burst_block_until = now + LOGIN_IP_BURST_BLOCK
        ip_state.suspicious_until = now + LOGIN_IP_SUSPICIOUS_WINDOW

    ip_state.suspicious_until = now + LOGIN_IP_SUSPICIOUS_WINDOW
    _update_reputation(ip_state, now, burst_hit=burst_hit)

    if ip_state.reputation_score >= 6 or ip_state.burst_strikes >= 3:
        ip_state.strong_block_until = now + LOGIN_STRONG_BLOCK

    user_state.save()
    ip_state.save()

    register_login_attempt(
        request=request,
        username=username,
        success=False,
        event_type=AuthSecurityEvent.EVENT_CAPTCHA_FAILED if reason == "captcha_failed" else AuthSecurityEvent.EVENT_LOGIN_FAILED,
        details={
            "reason": reason,
            "captcha_used": bool(captcha_used),
            "user_failed_count": user_state.failed_count,
            "ip_failed_count": ip_state.failed_count,
            "ip_burst_count": ip_state.burst_count,
        },
    )

    active_until = _active_block_candidates(user_state, ip_state, now=now)
    blocked_minutes = 0
    if active_until and active_until > now:
        blocked_minutes = int((active_until - now).total_seconds() // 60) or 1

    captcha_required = _captcha_required_for_state(user_state, now) or _captcha_required_for_state(ip_state, now)
    if ip_state.suspicious_until and ip_state.suspicious_until > now:
        captcha_required = True

    return LoginDecision(
        blocked=bool(active_until and active_until > now),
        blocked_until=active_until,
        blocked_minutes=blocked_minutes,
        captcha_required=captcha_required,
        user_state=user_state,
        ip_state=ip_state,
    )


def register_login_success(*, request, username: str, user_state: AuthSecurityState, ip_state: AuthSecurityState, user=None):
    now = timezone.now()
    _reset_user_login_state(user_state, now)
    _soften_ip_state_on_success(ip_state, now)
    register_login_attempt(
        request=request,
        username=username,
        success=True,
        user=user,
        event_type=AuthSecurityEvent.EVENT_LOGIN_SUCCESS,
        details={"ip": get_client_ip(request)},
    )


def register_logout(*, request, username: str = "", user=None):
    register_login_attempt(
        request=request,
        username=username,
        success=True,
        user=user,
        event_type=AuthSecurityEvent.EVENT_LOGOUT,
        details={},
    )


def login_recovery_key(request, namespace: str) -> str:
    return f"recovery:{namespace}:{get_client_ip(request)}"


def allow_recovery_request(request, namespace: str = "email") -> bool:
    key = login_recovery_key(request, namespace)
    now = timezone.now()
    state = cache.get(key, {"count": 0, "window": now})
    if state.get("window") and (now - state["window"]) > LOGIN_RECOVERY_WINDOW:
        state = {"count": 0, "window": now}
    state["count"] += 1
    cache.set(key, state, timeout=int(LOGIN_RECOVERY_WINDOW.total_seconds()))
    return state["count"] <= LOGIN_RECOVERY_MAX_REQUESTS
