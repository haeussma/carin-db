import { redirect } from 'next/navigation'

export default function HomePage() {
    // Redirect to /home by default
    redirect('/home')
}