export default function Footer() {
  return (
    <footer id="contact" className="px-6 pt-20 pb-10 border-t border-slate-200 dark:border-white/10">
      <div className="max-w-6xl mx-auto grid md:grid-cols-4 gap-10">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-display font-bold text-sm">
              S
            </div>
            <span className="font-display font-bold">StudentHub</span>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            One platform connecting students, faculty, and administration.
          </p>
        </div>

        <div>
          <h4 className="font-semibold mb-3 text-sm">Product</h4>
          <ul className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
            <li><a href="#features" className="hover:text-primary">Features</a></li>
            <li><a href="#about" className="hover:text-primary">About</a></li>
          </ul>
        </div>

        <div>
          <h4 className="font-semibold mb-3 text-sm">Portals</h4>
          <ul className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
            <li>Admin</li>
            <li>Faculty</li>
            <li>Student</li>
          </ul>
        </div>

        <div>
          <h4 className="font-semibold mb-3 text-sm">Contact</h4>
          <p className="text-sm text-slate-500 dark:text-slate-400">support@studenthub.edu</p>
        </div>
      </div>

      <p className="text-center text-xs text-slate-400 mt-14">
        © {new Date().getFullYear()} StudentHub. All rights reserved.
      </p>
    </footer>
  );
}
