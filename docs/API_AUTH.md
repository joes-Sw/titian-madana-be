# Dokumentasi API Autentikasi & Role

Panduan ini untuk tim Frontend agar dapat memakai fitur login berbasis role.

- Base URL (dev): `http://localhost:8000`
- Semua endpoint API diawali prefix `/api`
- Dokumentasi interaktif (Swagger UI): `http://localhost:8000/docs`
- Skema OpenAPI mentah: `http://localhost:8000/openapi.json`

## Ringkasan

- Login memakai **username + password + konfirmasi password**.
- **Tidak ada endpoint registrasi.** Akun dibuat oleh backend (seeding).
- Tersedia **3 role**: `superadmin`, `manager`, `marketing`.
- Login sukses mengembalikan **JWT**. Token dikirim di header
  `Authorization: Bearer <token>` untuk endpoint yang dilindungi.
- Role menentukan endpoint mana yang boleh diakses (lihat tabel di bawah).

## Akun Dummy untuk Uji Coba

| Role | Username | Password |
|------|----------|----------|
| superadmin | `superadmin` | `Superadmin#123` |
| manager | `manager` | `Manager#123` |
| marketing | `marketing` | `Marketing#123` |

> Ganti password ini sebelum production.

---

## 1. Login

`POST /api/auth/login`

### Request body

| Field | Tipe | Wajib | Keterangan |
|-------|------|-------|------------|
| `username` | string | ya | Minimal 3 karakter, tanpa spasi. Otomatis di-*trim* & lowercase. |
| `password` | string | ya | Minimal 6 karakter. |
| `confirm_password` | string | ya | Wajib sama persis dengan `password`. |

Contoh:

```json
{
  "username": "superadmin",
  "password": "Superadmin#123",
  "confirm_password": "Superadmin#123"
}
```

### Respons sukses — `200 OK`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 28800,
  "role": "superadmin",
  "username": "superadmin",
  "full_name": "Super Admin"
}
```

| Field | Keterangan |
|-------|------------|
| `access_token` | JWT untuk header Authorization. |
| `token_type` | Selalu `bearer`. |
| `expires_in` | Masa berlaku token (detik). Default 8 jam. |
| `role` | Role user, untuk menentukan menu/halaman di FE. |
| `username` | Username yang login. |
| `full_name` | Nama lengkap (bisa `null`). |

### Contoh JavaScript (fetch)

```js
async function login(username, password, confirmPassword) {
  const res = await fetch("http://localhost:8000/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username,
      password,
      confirm_password: confirmPassword,
    }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(typeof err.detail === "string" ? err.detail : "Validasi gagal");
  }
  return res.json(); // { access_token, role, ... }
}
```

### Contoh cURL

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"manager","password":"Manager#123","confirm_password":"Manager#123"}'
```

### Kemungkinan error

| Status | Penyebab | `detail` |
|--------|----------|----------|
| `401` | Username tidak ada **atau** password salah | `Username atau password salah` |
| `403` | Akun dinonaktifkan (`is_active=false`) | `Akun tidak aktif, hubungi superadmin` |
| `403` | Role user tidak dikenali | `Role '<role>' tidak dikenali` |
| `422` | Body tidak valid (password beda, password/username terlalu pendek, username ada spasi) | array error validasi |

Contoh respons `401`:

```json
{ "detail": "Username atau password salah" }
```

Contoh respons `422` (contoh password tidak sama):

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body"],
      "msg": "Value error, Password dan konfirmasi password tidak sama",
      "input": { "username": "manager", "password": "Manager#123", "confirm_password": "Manager#999" }
    }
  ]
}
```

---

## 2. Profil user yang sedang login

`GET /api/auth/me`

Header: `Authorization: Bearer <access_token>`

### Respons sukses — `200 OK`

```json
{
  "id": 1,
  "username": "superadmin",
  "role": "superadmin",
  "full_name": "Super Admin",
  "is_active": true,
  "created_at": "2026-01-01T08:00:00"
}
```

Berguna untuk memvalidasi token saat reload halaman dan mengambil data user.

### Kemungkinan error

| Status | Penyebab | `detail` |
|--------|----------|----------|
| `401` | Header Authorization tidak ada | `Token autentikasi tidak ditemukan` |
| `401` | Token rusak/tidak valid | `Token autentikasi tidak valid` |
| `401` | Token kedaluwarsa | `Token sudah kadaluarsa, silakan login kembali` |
| `403` | Akun dinonaktifkan setelah token dibuat | `Akun tidak aktif` |

---

## 3. Matriks hak akses

| Endpoint | Metode | Role yang diizinkan |
|----------|--------|---------------------|
| `/api/auth/login` | POST | publik (belum login) |
| `/api/auth/me` | GET | semua yang sudah login |
| `/api/admin/scrape` | POST | `superadmin`, `manager` |
| `/api/admin/scrape/runs` | GET | semua yang sudah login |
| `/api/tenders*` | GET | publik (belum diubah) |
| `/api/stats` | GET | publik (belum diubah) |

Bila login tetapi role tidak berhak, backend mengembalikan:

```json
{
  "detail": "Akses ditolak. Role 'marketing' tidak diizinkan untuk aksi ini (butuh: superadmin, manager)"
}
```

---

## 4. Panduan integrasi di Frontend

### a. Simpan token & role setelah login

```js
const data = await login(username, password, confirmPassword);
localStorage.setItem("token", data.access_token);
localStorage.setItem("role", data.role);
```

### b. Helper request ber-token

```js
async function apiFetch(url, options = {}) {
  const token = localStorage.getItem("token");
  const res = await fetch(`http://localhost:8000${url}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  if (res.status === 401) {
    localStorage.clear();
    window.location.href = "/login"; // token habis/tidak valid
    return;
  }
  if (res.status === 403) {
    throw new Error("Anda tidak punya akses ke fitur ini");
  }
  return res.json();
}
```

### c. Routing / menu berdasarkan role

```js
const role = localStorage.getItem("role");

const menuByRole = {
  superadmin: ["Dashboard", "Data Tender", "Riwayat Scrape", "Kelola Pengguna"],
  manager: ["Dashboard", "Data Tender", "Riwayat Scrape"],
  marketing: ["Dashboard", "Data Tender"],
};

const menu = menuByRole[role] || [];
```

### d. Verifikasi sesi saat reload

```js
async function restoreSession() {
  try {
    const user = await apiFetch("/api/auth/me");
    return user; // { username, role, ... }
  } catch {
    return null;
  }
}
```

### Tips

- `401` = belum login / token tidak valid atau kedaluwarsa → arahkan ke halaman login.
- `403` = sudah login tapi tidak punya hak → sembunyikan/disable tombolnya juga di UI
  (backend tetap jadi penentu akhir).
- Simpan token di `localStorage` untuk kemudahan, atau `httpOnly cookie` bila butuh
  keamanan lebih (perlu penyesuaian di backend).
- Waktu kedaluwarsa token ada di field `expires_in` (detik).
