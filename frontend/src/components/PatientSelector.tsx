import { useEffect, useState } from 'react'
import { api } from '../api/client'

// Shared hook: loads the psychologist's patient list once. Pages that render
// a patient <select> used to each copy this load + normalize logic (×5).
export function usePatientContext() {
  const [patients, setPatients] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getPsychPatients()
      .then((d: any) => setPatients(Array.isArray(d) ? d : []))
      .catch(() => setPatients([]))
      .finally(() => setLoading(false))
  }, [])

  return { patients, loading, setPatients }
}

export function patientKey(p: any): string {
  return p?.username || p
}

export function patientLabel(p: any): string {
  return p?.name || p
}

interface PatientSelectorProps {
  patients: any[]
  value: string
  onChange: (value: string) => void
  placeholder?: string
  style?: React.CSSProperties
}

// Shared patient <select> (was duplicated across PatientInsights, Timeline,
// ClinicalNotes, Followups, and others).
export default function PatientSelector({ patients, value, onChange, placeholder = '-- Select patient --', style }: PatientSelectorProps) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)} style={style}>
      <option value="">{placeholder}</option>
      {patients.map((p: any) => (
        <option key={patientKey(p)} value={patientKey(p)}>{patientLabel(p)}</option>
      ))}
    </select>
  )
}
