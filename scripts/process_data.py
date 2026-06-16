#!/usr/bin/env python3
"""
AI 对话数据归一化脚本

从浏览器扩展导出的 JSON 文件读取对话数据，统一格式输出为 data/conversations.json
- chat_data/microsoft_edge_extention/chatGPT/*.json
- chat_data/microsoft_edge_extention/gemini/*.json

用法:
    python scripts/process_data.py [--data-dir DATA_DIR] [--output OUTPUT]

输出:
    data/conversations.json   — 统一对话数据集
"""

import json
import os
import re
import sys

from datetime import datetime
from typing import Any, Optional

# ─── 分类关键词表 ────────────────────────────────────────────────

CATEGORY_RULES = {
    "论文撰写": [
        "修改论文", "system model", "缩写段落", "缩写内容", "致谢",
        "revision", "manuscript", "模版", "模板", "section",
        "introduction", "motivation", "摘要", "abstract",
    ],
    "审稿回复": [
        "审稿意见", "reviewer", "cover letter", "response", "回复",
        "minor revision", "point-by-point", "rebuttal",
    ],
    "格式排版": [
        "latex", "bibtex", "表格", "字体", "标点", "ieee",
        "格式", "间距", "上标", "标题大小写", "缩写冠词",
        "裁剪", "代码样式", "style manual",
    ],
    "英文润色": [
        "润色", "缩写规范", "语法", "editing", "refinement",
        "conciseness", "grammar", "省略号", "大写规范",
        "措辞", "语义歧义", "解释",
    ],
    "技术讨论": [
        "多模态", "plkg", "信道", "csi", "量化", "snr",
        "互信息", "llm", "密钥", "key generation",
        "fdd", "tde", "3gpp", "nlos", "uma", "nr",
        "特征", "归一化", "模型",
    ],
}


def classify(title: str) -> str:
    """根据标题关键词返回分类标签"""
    title_lower = title.lower()
    scores = {}
    for cat, keywords in CATEGORY_RULES.items():
        score = sum(1 for kw in keywords if kw.lower() in title_lower)
        if score > 0:
            scores[cat] = score
    if scores:
        return max(scores, key=scores.get)
    return "其他"








def parse_timestamp(ts: Any) -> Optional[datetime]:
    """尝试多种时间格式解析"""
    if isinstance(ts, (int, float)):
        # 毫秒级时间戳
        if ts > 1e12:
            ts = ts / 1000
        return datetime.fromtimestamp(ts)
    if isinstance(ts, str):
        for fmt in [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
        ]:
            try:
                return datetime.strptime(ts, fmt)
            except ValueError:
                continue
    return None


def extract_title_from_messages(messages: list[dict]) -> str:
    """从消息中提取有意义的标题"""
    for msg in messages:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            # 取第一段（最多 80 字）
            first_line = content.strip().split("\n")[0][:80]
            if first_line:
                return first_line
    return "未命名对话"


def extract_image_refs(contents: list[dict], base_dir: str) -> list[str]:
    """从 contents 中提取引用的图片路径"""
    refs = []
    for c in contents:
        if c.get("type") == "image":
            path = c.get("content", "")
            if path and os.path.exists(os.path.join(base_dir, path)):
                refs.append(path)
        elif c.get("type") == "text":
            # 检查文本中引用的本地图片
            for match in re.finditer(r'image_\w+\.(png|jpg|jpeg|gif)', c.get("content", "")):
                refs.append(match.group(0))
    return list(set(refs))


# ─── 浏览器扩展 JSON 解析 ────────────────────────────────────────

def parse_extension_json(filepath: str) -> Optional[dict]:
    """
    解析浏览器扩展导出的 JSON 文件（ChatGPT / Gemini 通用格式）
    返回归一化对话: {id, title, model, model_version, messages, created_at, source}
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"  [跳过] JSON 解析失败: {filepath} — {e}")
        return None

    if not isinstance(data, list) or len(data) == 0:
        return None

    # 按 chatGroupId 分组
    groups: dict[str, list[dict]] = {}
    model_info = {}
    for entry in data:
        gid = entry.get("chatGroupId", "ungrouped")
        groups.setdefault(gid, []).append(entry)
        if "displayModel" in entry:
            model_info[gid] = {
                "model": entry.get("displayModel", "Unknown"),
                "model_version": entry.get("modelId", ""),
            }

    # 对每个 group 构建对话
    results = []
    for gid, entries in groups.items():
        entries.sort(key=lambda e: e.get("created_at", 0))

        messages = []
        image_refs = []
        base_dir = os.path.dirname(filepath)

        for entry in entries:
            role = entry.get("role", "user")
            entry_ts = entry.get("created_at", None)
            contents = entry.get("contents", [])
            for c in contents:
                if c.get("type") == "text":
                    content = c.get("content", "").strip()
                    if content:
                        messages.append({"role": role, "content": content, "created_at": entry_ts})
                elif c.get("type") == "thinking":
                    content = c.get("content", "").strip()
                    if content:
                        messages.append({"role": "thinking", "content": content, "created_at": entry_ts})
                elif c.get("type") == "image":
                    img_path = c.get("content", "")
                    if img_path:
                        image_refs.append(img_path)

        if not messages:
            continue

        # 提取标题
        title = extract_title_from_messages(messages)

        # 时间
        first_ts = entries[0].get("created_at", 0)
        last_ts = entries[-1].get("created_at", first_ts)
        dt = parse_timestamp(first_ts)
        ts_val = dt.timestamp() if dt else 0

        info = model_info.get(gid, {"model": "Unknown", "model_version": ""})

        results.append({
            "id": gid,
            "title": title,
            "category": classify(title),
            "model": info["model"],
            "model_version": info["model_version"],
            "source": os.path.basename(os.path.dirname(os.path.dirname(filepath))),
            "source_file": os.path.basename(filepath),
            "created_at": dt.isoformat() if dt else None,
            "timestamp": ts_val,
            "message_count": len(messages),
            "messages": messages,
            "image_refs": image_refs,
        })

    return results if results else None





# ─── 主流程 ──────────────────────────────────────────────────────

def scan_directory(data_dir: str) -> list[dict]:
    """扫描数据目录，解析所有对话"""
    all_conversations = []

    # ── 1. 浏览器扩展: ChatGPT ──
    chatgpt_dir = os.path.join(data_dir, "microsoft_edge_extention", "chatGPT")
    if os.path.isdir(chatgpt_dir):
        print(f"扫描 ChatGPT 目录: {chatgpt_dir}")
        for fname in sorted(os.listdir(chatgpt_dir)):
            if fname.endswith(".json"):
                fpath = os.path.join(chatgpt_dir, fname)
                print(f"  解析: {fname}")
                result = parse_extension_json(fpath)
                if result:
                    all_conversations.extend(result)
                    print(f"    → {len(result)} 个对话")
    else:
        print(f"[跳过] ChatGPT 目录不存在: {chatgpt_dir}")

    # ── 2. 浏览器扩展: Gemini ──
    gemini_dir = os.path.join(data_dir, "microsoft_edge_extention", "gemini")
    if os.path.isdir(gemini_dir):
        print(f"扫描 Gemini 目录: {gemini_dir}")
        for fname in sorted(os.listdir(gemini_dir)):
            if fname.endswith(".json"):
                fpath = os.path.join(gemini_dir, fname)
                print(f"  解析: {fname}")
                result = parse_extension_json(fpath)
                if result:
                    all_conversations.extend(result)
                    print(f"    → {len(result)} 个对话")
    else:
        print(f"[跳过] Gemini 目录不存在: {gemini_dir}")

    return all_conversations


def deduplicate(conversations: list[dict]) -> list[dict]:
    """基于标题和时间的简单去重"""
    seen = set()
    unique = []
    for conv in conversations:
        key = (conv["title"], conv.get("created_at", ""))
        if key not in seen:
            seen.add(key)
            unique.append(conv)
    return unique


def split_by_date(conversations: list[dict]) -> list[dict]:
    """按消息实际日期拆分对话 —— 跨天 session 每天显示一次"""
    result = []
    for conv in conversations:
        # 按日期分组消息
        day_groups: dict[str, list] = {}
        for m in conv.get("messages", []):
            ts = m.get("created_at")
            if not ts:
                # 没有时间戳的消息归入对话首条日期
                day = conv.get("created_at", "")[:10] if conv.get("created_at") else "unknown"
            else:
                ts_str = str(ts)
                if "T" in ts_str:
                    day = ts_str[:10]
                elif " " in ts_str:
                    day = ts_str[:10]
                else:
                    day = conv.get("created_at", "")[:10] if conv.get("created_at") else "unknown"
            day_groups.setdefault(day, []).append(m)

        # 为每个有天消息的日期创建一个对话条目
        for day, msgs in day_groups.items():
            entry = dict(conv)  # shallow copy
            entry["messages"] = msgs
            entry["message_count"] = len(msgs)
            entry["created_at"] = day + "T00:00:00"  # 日期精确到日
            # 用该日第一条用户消息作为该日小标题
            for m in msgs:
                if m.get("role") == "user":
                    first_line = m.get("content", "").strip().split("\n")[0][:80]
                    if first_line:
                        entry["title"] = first_line
                    break
            # 用该日第一条消息的时间作为 timestamp
            first_msg_ts = msgs[0].get("created_at")
            if first_msg_ts:
                dt = parse_timestamp(str(first_msg_ts))
                entry["timestamp"] = dt.timestamp() if dt else 0
            else:
                entry["timestamp"] = conv.get("timestamp", 0)
            result.append(entry)

    return result


def build_statistics(conversations: list[dict]) -> dict:
    """构建统计信息"""
    model_count = {}
    category_count = {}
    monthly = {}

    for conv in conversations:
        model = conv.get("model", "Unknown")
        model_count[model] = model_count.get(model, 0) + 1

        cat = conv.get("category", "其他")
        category_count[cat] = category_count.get(cat, 0) + 1

        if conv.get("created_at"):
            try:
                month = conv["created_at"][:7]  # YYYY-MM
                monthly[month] = monthly.get(month, 0) + 1
            except (IndexError, TypeError):
                pass

    return {
        "total": len(conversations),
        "by_model": model_count,
        "by_category": category_count,
        "by_month": dict(sorted(monthly.items())),
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="AI 对话数据归一化工具")
    parser.add_argument(
        "--data-dir",
        default="chat_data",
        help="数据目录路径（默认: chat_data）",
    )
    parser.add_argument(
        "--output",
        default="data/conversations.json",
        help="输出文件路径（默认: data/conversations.json）",
    )
    args = parser.parse_args()

    data_dir = os.path.abspath(args.data_dir)
    if not os.path.isdir(data_dir):
        print(f"错误: 数据目录不存在: {data_dir}")
        sys.exit(1)

    print("=" * 60)
    print("AI 对话数据归一化")
    print("=" * 60)

    # 扫描
    conversations = scan_directory(data_dir)
    print(f"\n原始对话数: {len(conversations)}")

    # 去重
    conversations = deduplicate(conversations)
    print(f"去重后对话数: {len(conversations)}")

    # 按日期拆分跨天对话
    conversations = split_by_date(conversations)
    print(f"按日期拆分后: {len(conversations)} 条")

    # 拆分后再去重（同 session 同日可能产生重复标题）
    conversations = deduplicate(conversations)
    print(f"去重后: {len(conversations)} 条")

    # 按时间排序
    conversations.sort(key=lambda c: c.get("timestamp", 0))

    # 统计数据
    stats = build_statistics(conversations)

    # 构建输出
    output = {
        "generated_at": datetime.now().isoformat(),
        "statistics": stats,
        "conversations": conversations,
    }

    # 写入
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 已写入: {os.path.abspath(args.output)}")
    print(f"  共 {len(conversations)} 个对话")
    print(f"  分类: {json.dumps(stats['by_category'], ensure_ascii=False)}")
    print(f"  模型: {json.dumps(stats['by_model'], ensure_ascii=False)}")
    print(f"  时间跨度: {min(stats['by_month'].keys())} ~ {max(stats['by_month'].keys())}" if stats['by_month'] else "  时间跨度: N/A")


if __name__ == "__main__":
    main()
