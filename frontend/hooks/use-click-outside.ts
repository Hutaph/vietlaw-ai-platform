/**
 * Hook tái sử dụng để phát hiện click bên ngoài element.
 * Dùng cho cả CategoryDropdown và ProviderSelector.
 */
import { useEffect, type RefObject } from 'react';

export function useClickOutside(
  ref: RefObject<HTMLElement | null>,
  onClickOutside: () => void
) {
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        onClickOutside();
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [ref, onClickOutside]);
}
