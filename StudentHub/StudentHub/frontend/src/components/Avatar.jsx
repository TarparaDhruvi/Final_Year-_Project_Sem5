/** Profile photo if the user uploaded one, otherwise a gradient circle with their initial. */
export default function Avatar({ user, size = 36, className = "" }) {
  const style = { width: size, height: size, fontSize: Math.max(12, size * 0.4) };
  if (user?.avatar_url) {
    return (
      <img
        src={user.avatar_url}
        alt={user.full_name || "Profile"}
        style={style}
        className={`rounded-full object-cover flex-shrink-0 ${className}`}
      />
    );
  }
  return (
    <div
      style={style}
      className={`rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-semibold flex-shrink-0 ${className}`}
    >
      {user?.full_name?.[0]?.toUpperCase() || "?"}
    </div>
  );
}
