export const metadata = {
  title: 'CEREBRON OMEGA',
  description: 'Orchestrateur multi-agents experimental'
}

export default function RootLayout({ children }) {
  return (
    <html lang="fr">
      <body style={{ margin: 0, fontFamily: 'Arial, sans-serif', background: '#f7f7f8', color: '#111' }}>
        {children}
      </body>
    </html>
  )
}
