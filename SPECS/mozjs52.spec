%global major 52

# Require libatomic for ppc
%ifarch ppc
%global system_libatomic 1
%endif

# Big endian platforms
%ifarch ppc ppc64 s390 s390x
%global big_endian 1
%endif

Name:           mozjs%{major}
Version:        52.9.0
Release:        2%{?dist}
Summary:        SpiderMonkey JavaScript library

License:        MPLv2.0 and MPLv1.1 and BSD and GPLv2+ and GPLv3+ and LGPLv2.1 and LGPLv2.1+ and AFL and ASL 2.0
URL:            https://developer.mozilla.org/en-US/docs/Mozilla/Projects/SpiderMonkey
Source0:        https://ftp.mozilla.org/pub/firefox/releases/%{version}esr/source/firefox-%{version}esr.source.tar.xz

# Patches from Debian mozjs52_52.3.1-4.debian.tar.xz:
Patch0001:      fix-soname.patch
Patch0002:      copy-headers.patch
Patch0003:      tests-increase-timeout.patch
Patch0004:      tests-snans-be.patch

# Disable JS Helper threads on ppc64le
# https://bugzilla.redhat.com/show_bug.cgi?id=1523121
Patch0010:      disable-extra-threads.patch

# Patches from https://github.com/ptomato/mozjs / Debian mozjs52_52.3.1-4.debian.tar.xz
Patch0101:      disable-mozglue.patch
Patch0104:      include-configure-script.patch

# Patches from Fedora firefox package:
Patch18:        xulrunner-24.0-jemalloc-ppc.patch
Patch19:        xulrunner-24.0-s390-inlines.patch
Patch26:        build-icu-big-endian.patch
Patch36:        build-missing-xlocale-h.patch
Patch304:       mozilla-1253216.patch

BuildRequires:  autoconf213
BuildRequires:  perl-devel
BuildRequires:  pkgconfig(libffi)
BuildRequires:  pkgconfig(zlib)
BuildRequires:  python2-devel
BuildRequires:  readline-devel
BuildRequires:  /usr/bin/zip
%if 0%{?system_libatomic}
BuildRequires:  libatomic
%endif

# Firefox does not allow to build with system version of jemalloc
Provides: bundled(jemalloc) = 4.3.1

%description
SpiderMonkey is the code-name for Mozilla Firefox's C++ implementation of
JavaScript. It is intended to be embedded in other applications
that provide host environments for JavaScript.

%package        devel
Summary:        Development files for %{name}
Requires:       %{name}%{?_isa} = %{version}-%{release}

%description    devel
The %{name}-devel package contains libraries and header files for
developing applications that use %{name}.

%prep
%setup -q -n firefox-%{version}esr/js/src

pushd ../..
%patch0001 -p1
%patch0002 -p1
%patch0003 -p1
%patch0004 -p1

%patch0010 -p1

%patch0101 -p1
%patch0104 -p1

%patch18 -p1 -b .jemalloc-ppc
%patch19 -p2 -b .s390-inlines

# Patch for big endian platforms only
%if 0%{?big_endian}
%patch26 -p1 -b .icu
%patch36 -p2 -b .xlocale
%endif

%patch304 -p1 -b .1253216

# make sure we don't ever accidentally link against bundled security libs
rm -rf security/
popd

# Remove zlib directory (to be sure using system version)
rm -rf ../../modules/zlib

%build
# Disable null pointer gcc6 optimization in gcc6 (rhbz#1328045)
export CFLAGS="%{optflags} -fno-tree-vrp -fno-strict-aliasing -fno-delete-null-pointer-checks"
export CXXFLAGS="$CFLAGS"
export LINKFLAGS="%{?__global_ldflags}"
export PYTHON="%{__python2}"
# Keep using Python 2 for the build for now
# https://bugzilla.redhat.com/show_bug.cgi?id=1610009
export RHEL_ALLOW_PYTHON2_FOR_BUILD=1

autoconf-2.13
%configure \
  --without-system-icu \
  --enable-posix-nspr-emulation \
  --with-system-zlib \
  --enable-tests \
  --disable-strip \
  --with-intl-api \
  --enable-readline \
  --enable-shared-js \
  --disable-optimize \
  --enable-pie \
%ifarch s390 s390x
  --disable-jemalloc \
%endif
%ifarch %{arm} aarch64 ppc %{power64}
  --disable-ion
%endif

%if 0%{?big_endian}
echo "Generate big endian version of config/external/icu/data/icud58l.dat"
pushd ../..
  ./mach python intl/icu_sources_data.py .
  ls -l config/external/icu/data
  rm -f config/external/icu/data/icudt*l.dat
popd
%endif

%make_build

%install
# Keep using Python 2 for the build for now
# https://bugzilla.redhat.com/show_bug.cgi?id=1610009
export RHEL_ALLOW_PYTHON2_FOR_BUILD=1

%make_install

# Fix permissions
chmod -x %{buildroot}%{_libdir}/pkgconfig/*.pc

# Remove unneeded files
rm %{buildroot}%{_bindir}/js%{major}-config
rm %{buildroot}%{_libdir}/libjs_static.ajs

# Rename library and create symlinks, following fix-soname.patch
mv %{buildroot}%{_libdir}/libmozjs-%{major}.so \
   %{buildroot}%{_libdir}/libmozjs-%{major}.so.0.0.0
ln -s libmozjs-%{major}.so.0.0.0 %{buildroot}%{_libdir}/libmozjs-%{major}.so.0
ln -s libmozjs-%{major}.so.0 %{buildroot}%{_libdir}/libmozjs-%{major}.so

%check
# Run SpiderMonkey tests
/usr/bin/python2-for-tests tests/jstests.py -d -s -t 1800 --no-progress ../../js/src/js/src/shell/js \
%ifarch %{ix86} x86_64 %{arm} aarch64 ppc ppc64le s390
;
%else
|| :
%endif

# Run basic JIT tests
/usr/bin/python2-for-tests jit-test/jit_test.py -s -t 1800 --no-progress ../../js/src/js/src/shell/js basic \
%ifarch %{ix86} x86_64 %{arm} aarch64 ppc ppc64le s390
;
%else
|| :
%endif

%ldconfig_scriptlets

%files
%doc README.html
%{_libdir}/libmozjs-%{major}.so.0*

%files devel
%{_bindir}/js%{major}
%{_libdir}/libmozjs-%{major}.so
%{_libdir}/pkgconfig/*.pc
%{_includedir}/mozjs-%{major}/

%changelog
* Mon Feb 10 2020 Kalev Lember <klember@redhat.com> - 52.9.0-2
- Rebuild for CET notes
- Resolves: #1657318

* Wed Jul 25 2018 Kalev Lember <klember@redhat.com> - 52.9.0-1
- Update to 52.9.0

* Mon Jun 11 2018 Ray Strode <rstrode@redhat.com> - 52.8.0-2
- safeguard against linking against bundled nss
  Related: #1563708

* Fri May 11 2018 Kalev Lember <klember@redhat.com> - 52.8.0-1
- Update to 52.8.0
- Fix the build on ppc
- Disable JS Helper threads on ppc64le (#1523121)

* Sat Apr 07 2018 Kalev Lember <klember@redhat.com> - 52.7.3-1
- Update to 52.7.3

* Tue Mar 20 2018 Kalev Lember <klember@redhat.com> - 52.7.2-1
- Update to 52.7.2
- Switch to %%ldconfig_scriptlets

* Thu Feb 08 2018 Fedora Release Engineering <releng@fedoraproject.org> - 52.6.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Tue Jan 23 2018 Kalev Lember <klember@redhat.com> - 52.6.0-1
- Update to 52.6.0

* Fri Nov 24 2017 Björn Esser <besser82@fedoraproject.org> - 52.5.0-5
- SpiderMonkey tests have regressions on %%{power64}, too

* Fri Nov 24 2017 Björn Esser <besser82@fedoraproject.org> - 52.5.0-4
- SpiderMonkey tests have regressions on big endian platforms

* Fri Nov 24 2017 Björn Esser <besser82@fedoraproject.org> - 52.5.0-3
- SpiderMonkey tests do not fail on any arch
- Basic JIT tests are failing on s390 arches, only
- Use macro for ppc64 arches
- Run tests using Python2 explicitly
- Simplify %%check
- Use the %%{major} macro consequently
- Replace %%define with %%global

* Fri Nov 24 2017 Björn Esser <besser82@fedoraproject.org> - 52.5.0-2
- Use macro for Python 2 interpreter
- Use proper export and quoting

* Tue Nov 14 2017 Kalev Lember <klember@redhat.com> - 52.5.0-1
- Update to 52.5.0

* Tue Oct 31 2017 Kalev Lember <klember@redhat.com> - 52.4.0-3
- Include standalone /usr/bin/js52 interpreter

* Tue Oct 31 2017 Kalev Lember <klember@redhat.com> - 52.4.0-2
- Various secondary arch fixes

* Thu Sep 28 2017 Kalev Lember <klember@redhat.com> - 52.4.0-1
- Update to 52.4.0

* Wed Sep 20 2017 Kalev Lember <klember@redhat.com> - 52.3.0-1
- Initial Fedora packaging, based on earlier mozjs45 work
