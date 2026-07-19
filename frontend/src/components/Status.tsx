import { AlertTriangle, CheckCircle2, CircleDashed, ShieldAlert, Send } from 'lucide-react'
import { FINAL_STATUS_LABELS, PRODUCT_LABELS, type ArtifactStatus, type FinalStatus, type ProductType } from '../domain'

export function FinalStatusPill({ status, approvalStatus, currentRole }: { status: FinalStatus; approvalStatus?: string | null; currentRole?: string | null }) {
  if (approvalStatus === 'APPROVED') {
    return <span className="final-pill ready_for_human_review"><CheckCircle2 size={13} />Đã duyệt</span>
  }
  if (approvalStatus === 'TRANSFERRED') {
    const roleLabel = currentRole === 'MANAGER' ? 'Quản lý' : currentRole === 'DIRECTOR' ? 'Giám đốc' : 'Chuyên viên'
    return <span className="final-pill needs_more_evidence"><Send size={13} />Chờ duyệt ({roleLabel})</span>
  }
  const Icon = status === 'READY_FOR_HUMAN_REVIEW' ? CheckCircle2 : status === 'BLOCKED' ? ShieldAlert : status === 'IN_PROGRESS' ? CircleDashed : AlertTriangle
  return <span className={`final-pill ${status.toLowerCase()}`}><Icon size={13} />{FINAL_STATUS_LABELS[status]}</span>
}

export function ArtifactPill({ status }: { status: ArtifactStatus }) {
  const labels: Record<ArtifactStatus, string> = { PASS: 'Đạt', WARNING: 'Cảnh báo', BLOCKED: 'Bị chặn', REVIEW_REQUIRED: 'Cần rà soát' }
  return <span className={`artifact-pill ${status.toLowerCase()}`}>{labels[status]}</span>
}

export function ProductPill({ product }: { product: ProductType }) {
  return <span className={`product-pill ${product.toLowerCase()}`}>{PRODUCT_LABELS[product]}</span>
}

