# snatch.spec: OBS recipe for openSUSE Tumbleweed (SNAT-0028).
#
# Ships Snatch's own source under /usr/share/snatch, run by the system's
# Python. Python, Tk, Pillow, ffmpeg, yt-dlp and QuickJS come from Tumbleweed.
# The empty snatch/INSTALLED_BY_PACKAGE written in %install is what tells the
# app it was installed by a package: its data then goes to
# $XDG_DATA_HOME/snatch, and it never offers its own updates.

Name:           snatch
# Placeholder: the set_version service (_service) writes the real version
# from the release tag. tests/test_package_install.py requires it to stay 0.
Version:        0
Release:        0
Summary:        Download and play videos with yt-dlp
License:        MIT
URL:            https://github.com/milnet01/snatch
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

# For %check, which imports every module and loads Tcl.
BuildRequires:  python3
BuildRequires:  python3-tk
BuildRequires:  python3-Pillow-tk
BuildRequires:  python3-cryptography
# Owns the hicolor directories the icons land in, for the filelist check.
BuildRequires:  hicolor-icon-theme

Requires:       python3 >= 3.10
Requires:       python3-tk
Requires:       python3-Pillow
Requires:       python3-Pillow-tk
# snatch.self_update imports it, and --selftest imports every module.
Requires:       python3-cryptography
# The fallback yt-dlp. Snatch offers the current one on first launch.
Requires:       yt-dlp
# yt-dlp's JavaScript runtime for YouTube; installs /usr/bin/qjs.
Requires:       quickjs
Requires:       ffmpeg
Requires:       hicolor-icon-theme
# The in-app player. Without it, videos open in the browser.
Recommends:     mpv

%description
Snatch is a desktop window for yt-dlp. Paste a link, pick a format and
download it, or search and play videos without leaving the app. On first
launch it offers to download the current yt-dlp, which YouTube needs, into
your home folder.

%prep
%setup -q

%build
# Nothing to build: the package ships source.

%install
install -d %{buildroot}%{_datadir}/snatch
cp -r snatch.py snatch icon.png %{buildroot}%{_datadir}/snatch/
find %{buildroot}%{_datadir}/snatch -type d -name __pycache__ -prune -exec rm -rf {} +
find %{buildroot}%{_datadir}/snatch -type f -exec chmod 0644 {} +
find %{buildroot}%{_datadir}/snatch -type d -exec chmod 0755 {} +
touch %{buildroot}%{_datadir}/snatch/snatch/INSTALLED_BY_PACKAGE
# Byte-compiled here, so no user run tries to write __pycache__ into a
# read-only folder. Hash-checked, so a changed file mtime cannot stale it.
python3 -m compileall -q -f --invalidation-mode checked-hash \
    -s %{buildroot} -p / %{buildroot}%{_datadir}/snatch

install -Dm0755 packaging/obs/snatch.sh %{buildroot}%{_bindir}/snatch
install -Dm0644 packaging/obs/io.github.milnet01.snatch.desktop \
    %{buildroot}%{_datadir}/applications/io.github.milnet01.snatch.desktop
install -Dm0644 packaging/obs/io.github.milnet01.snatch.metainfo.xml \
    %{buildroot}%{_datadir}/metainfo/io.github.milnet01.snatch.metainfo.xml
install -Dm0644 icon_48.png \
    %{buildroot}%{_datadir}/icons/hicolor/48x48/apps/io.github.milnet01.snatch.png
install -Dm0644 icon_64.png \
    %{buildroot}%{_datadir}/icons/hicolor/64x64/apps/io.github.milnet01.snatch.png
install -Dm0644 icon.png \
    %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/io.github.milnet01.snatch.png

%check
# The staged tree, not an installed copy. XDG_DATA_HOME inside the build
# directory keeps the result off the build machine's $HOME.
XDG_DATA_HOME="$PWD/selftest-data" \
    python3 %{buildroot}%{_datadir}/snatch/snatch.py --selftest

# No post-install scriptlet: Tumbleweed's file triggers refresh the icon
# cache and the desktop database.

%files
%license LICENSE
%doc README.md
%{_bindir}/snatch
%{_datadir}/snatch
%{_datadir}/applications/io.github.milnet01.snatch.desktop
%{_datadir}/metainfo/io.github.milnet01.snatch.metainfo.xml
%{_datadir}/icons/hicolor/*/apps/io.github.milnet01.snatch.png

%changelog
