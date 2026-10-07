import ContactsIcon from '@/components/Icons/ContactsIcon.vue'
import DealsIcon from '@/components/Icons/DealsIcon.vue'
import LeadsIcon from '@/components/Icons/LeadsIcon.vue'
import NoteIcon from '@/components/Icons/NoteIcon.vue'
import OrganizationsIcon from '@/components/Icons/OrganizationsIcon.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import TaskIcon from '@/components/Icons/TaskIcon.vue'
import LucideLayoutDashboard from '~icons/lucide/layout-dashboard'
import Email2Icon from '@/components/Icons/Email2Icon.vue'
import CalendarIcon from '@/components/Icons/CalendarIcon.vue'
import WhatsAppIcon from '@/components/Icons/WhatsAppIcon.vue'
import SparkleIcon from '@/components/Icons/SparkleIcon.vue'
import LucideInstagram from '~icons/lucide/instagram'
import router from '@/router'

// Panda Project V2: menu em grupos separados por divisor.
// Grupo 1: trabalho do dia a dia. Grupo 2: contatos e canais.
// (Leads, Organizações, Notas e Ligações continuam existindo como rotas,
// mas ficam fora do menu; Contatos passa a unificar leads + contatos.)
// Itens cujas rotas ainda não existem (Calendário, E-mail, WhatsApp,
// Instagram, Agente de IA) são ocultados automaticamente por router.hasRoute.
export const navigationItems = [
  {
    label: 'Dashboard',
    icon: LucideLayoutDashboard,
    route: 'Dashboard',
    desktopOnly: true,
    group: 1,
  },
  { label: 'Deals', icon: DealsIcon, route: 'Deals', group: 1 },
  { label: 'Tasks', icon: TaskIcon, route: 'Tasks', group: 1 },
  { label: 'Contacts', icon: ContactsIcon, route: 'Contacts', group: 2 },
  { label: 'Calendar', icon: CalendarIcon, route: 'Calendar', group: 2 },
  { label: 'Email', icon: Email2Icon, route: 'Inbox', group: 2 },
  { label: 'WhatsApp', icon: WhatsAppIcon, route: 'WhatsApp', group: 2 },
  { label: 'Instagram', icon: LucideInstagram, route: 'Instagram', group: 2 },
  { label: 'AI Agent', icon: SparkleIcon, route: 'Agente', group: 3 },
]

export function getNavigationItems({ mobile = false } = {}) {
  return navigationItems.filter(
    (item) => router.hasRoute(item.route) && (!mobile || !item.desktopOnly),
  )
}
