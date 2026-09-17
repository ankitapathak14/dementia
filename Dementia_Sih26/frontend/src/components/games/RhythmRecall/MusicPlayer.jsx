/**
 * MusicPlayer.jsx — Reusable accessible audio player for Rhythm & Recall
 * ========================================================================
 * Handles audio loading, playback, errors, and fallback gracefully.
 * Designed for elderly users — large controls, clear state, kind error messages.
 */
import { useState, useRef, useEffect } from "react";

const LIME = "#C8F135";

export default function MusicPlayer({
  audioUrl,
  title,
  artist,
  onEnded,
  onError,
  autoPlay = false,
  showProgress = true,
  accentColor = LIME,
}) {
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    // Reset state when URL changes
    setIsPlaying(false);
    setIsLoading(false);
    setHasError(false);
    setCurrentTime(0);
    setDuration(0);
  }, [audioUrl]);

  useEffect(() => {
    if (autoPlay && audioRef.current && audioUrl) {
      handlePlay();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoPlay, audioUrl]);

  function handlePlay() {
    const audio = audioRef.current;
    if (!audio || !audioUrl) return;
    setIsLoading(true);
    setHasError(false);
    audio.play().then(() => {
      setIsPlaying(true);
      setIsLoading(false);
    }).catch(() => {
      setIsLoading(false);
      setHasError(true);
      if (onError) onError("Could not play audio.");
    });
  }

  function handlePause() {
    const audio = audioRef.current;
    if (!audio) return;
    audio.pause();
    setIsPlaying(false);
  }

  function handleTimeUpdate() {
    const audio = audioRef.current;
    if (audio) setCurrentTime(audio.currentTime);
  }

  function handleLoadedMetadata() {
    const audio = audioRef.current;
    if (audio) setDuration(audio.duration);
    setIsLoading(false);
  }

  function handleAudioError() {
    setIsPlaying(false);
    setIsLoading(false);
    setHasError(true);
    if (onError) onError("Music couldn't be loaded. Let's try another song.");
  }

  function handleEnded() {
    setIsPlaying(false);
    setCurrentTime(0);
    if (onEnded) onEnded();
  }

  function handleSeek(e) {
    const audio = audioRef.current;
    if (!audio || !duration) return;
    const pct = parseFloat(e.target.value);
    audio.currentTime = (pct / 100) * duration;
    setCurrentTime(audio.currentTime);
  }

  function handleVolumeChange(e) {
    const val = parseFloat(e.target.value);
    setVolume(val);
    if (audioRef.current) audioRef.current.volume = val;
  }

  const progressPct = duration > 0 ? (currentTime / duration) * 100 : 0;

  const formatTime = (s) => {
    if (!isFinite(s)) return "0:00";
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec < 10 ? "0" : ""}${sec}`;
  };

  return (
    <div
      style={{
        background: "rgba(10,12,10,0.92)",
        border: `1px solid ${accentColor}33`,
        borderRadius: 20,
        padding: "20px 24px",
        width: "100%",
      }}
      role="region"
      aria-label="Music Player"
    >
      {/* Hidden HTML audio element */}
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onEnded={handleEnded}
          onError={handleAudioError}
          onWaiting={() => setIsLoading(true)}
          onCanPlay={() => setIsLoading(false)}
          preload="metadata"
        />
      )}

      {/* Track Info */}
      <div style={{ marginBottom: 16, textAlign: "center" }}>
        <div style={{ fontSize: 32, marginBottom: 8 }}>🎵</div>
        <div style={{ fontSize: 18, fontWeight: 800, color: "#fff", marginBottom: 4 }}>
          {title || "♪ Now Playing"}
        </div>
        {artist && (
          <div style={{ fontSize: 14, color: "#9ca3af" }}>{artist}</div>
        )}
      </div>

      {/* Error state */}
      {hasError && (
        <div
          style={{
            background: "rgba(251,191,36,0.10)",
            border: "1px solid rgba(251,191,36,0.30)",
            borderRadius: 12,
            padding: "12px 16px",
            marginBottom: 16,
            textAlign: "center",
            color: "#fbbf24",
            fontSize: 15,
          }}
          role="alert"
        >
          🎵 Music couldn't be loaded. Let's try another song.
        </div>
      )}

      {/* Play / Pause button */}
      {!hasError && (
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 20 }}>
          <button
            onClick={isPlaying ? handlePause : handlePlay}
            disabled={!audioUrl || isLoading}
            aria-label={isPlaying ? "Pause music" : "Play music"}
            style={{
              width: 80,
              height: 80,
              borderRadius: "50%",
              background: isPlaying
                ? `rgba(200,241,53,0.15)`
                : accentColor,
              border: `3px solid ${accentColor}`,
              color: isPlaying ? accentColor : "#080808",
              fontSize: 32,
              cursor: audioUrl && !isLoading ? "pointer" : "not-allowed",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.2s ease",
              boxShadow: isPlaying ? `0 0 24px ${accentColor}44` : `0 6px 20px ${accentColor}44`,
              opacity: !audioUrl ? 0.5 : 1,
            }}
          >
            {isLoading ? "⏳" : isPlaying ? "⏸" : "▶"}
          </button>
        </div>
      )}

      {/* Progress bar */}
      {showProgress && duration > 0 && (
        <div style={{ marginBottom: 12 }}>
          <input
            type="range"
            min={0}
            max={100}
            value={progressPct}
            onChange={handleSeek}
            aria-label="Playback position"
            style={{ width: "100%", accentColor, height: 6 }}
          />
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#9ca3af", marginTop: 4 }}>
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>
      )}

      {/* Volume */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 18 }} aria-hidden="true">🔊</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={volume}
          onChange={handleVolumeChange}
          aria-label="Volume"
          style={{ flex: 1, accentColor, height: 4 }}
        />
      </div>
    </div>
  );
}
