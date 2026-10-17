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
  { href: 'saajha/',       hi: 'साझा कीजिए',     en: 'Share' },
];

export const CONTACT = {
  address: {
    hi: 'लोधा कॉलोनी धर्मशाला, महाराणा प्रताप चौराहा, महूनाका इंदौर, मध्यप्रदेश',
    en: 'Lodha Colony Dharmshala, Maharana Pratap Chauraha, Mhow Naka, Indore, MP',
  },
  phone: '+91 90987 81740',
  // The समाज's own address, given by them. The footer renders it from here; the
  // संपर्क pages carry their own row, because that list is static HTML.
  email: 'lodhasamajindore@gmail.com',
  // `brand` is the colour the icon takes under the pointer - each platform's
  // own, so the footer's four gold discs are told apart at a glance.
  socials: [
    { label: 'Facebook',  brand: '#1877f2', href: 'https://www.facebook.com/profile.php?id=61552495104262' },
    { label: 'Instagram', brand: '#e1306c', href: 'https://www.instagram.com/lodha.samaj/' },
    { label: 'YouTube',   brand: '#ff0033', href: 'https://www.youtube.com/@lodhasamajindore2762' },
    { label: 'WhatsApp',  brand: '#25d366', href: 'https://wa.me/919098781740' },
  ],
};
