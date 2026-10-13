export const NAV = [
  { href: '',             hi: 'होम',            en: 'Home' },
  { href: 'karyakram/',    hi: 'कार्यक्रम',      en: 'Events' },
  { href: 'daan/',        hi: 'दान',            en: 'Donate' },
  { href: 'shiksha/',      hi: 'शिक्षा',         en: 'Education' },
  { href: 'swasthya/',     hi: 'स्वास्थ्य',      en: 'Health' },
  { href: 'parichay/',     hi: 'हमारे बारे में', en: 'About' },
  { href: 'padadhikari/',  hi: 'पदाधिकारी',      en: 'Office bearers' },
  { href: 'gallery/',      hi: 'गैलरी',          en: 'Gallery' },
  { href: 'panjiyan/',     hi: 'पंजीयन',         en: 'Register' },
  { href: 'sampark/',      hi: 'संपर्क',         en: 'Contact' },
];

export const CONTACT = {
  address: {
    hi: 'लोधा कॉलोनी धर्मशाला, महाराणा प्रताप चौराहा, महूनाका इंदौर, मध्यप्रदेश',
    en: 'Lodha Colony Dharmshala, Maharana Pratap Chauraha, Mhow Naka, Indore, MP',
  },
  phone: '+91 98263 24370',
  // No email: the समाज decided the phone number is the only contact route, rather
  // than publish an address nobody reads. To add one later, set `email` here - the
  // footer and the संपर्क pages pick it up on their own.
  email: null,
  socials: [
    { label: 'Facebook',  href: 'https://www.facebook.com/profile.php?id=61552495104262' },
    { label: 'Instagram', href: 'https://www.instagram.com/lodha.samaj/' },
    { label: 'YouTube',   href: 'https://www.youtube.com/@lodhasamajindore2762' },
    { label: 'WhatsApp',  href: 'https://wa.me/919826324370' },
  ],
};
