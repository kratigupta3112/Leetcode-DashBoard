"""Probe LeetCode GraphQL for compensation posts."""
import httpx
import json

HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com/discuss/compensation",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

LIST_QUERY = {
    "operationName": "discussPostItems",
    "query": (
        "query discussPostItems($orderBy: ArticleOrderByEnum, $keywords: [String]!, "
        "$tagSlugs: [String!], $skip: Int, $first: Int) {\n"
        "  ugcArticleDiscussionArticles(\n"
        "    orderBy: $orderBy\n"
        "    keywords: $keywords\n"
        "    tagSlugs: $tagSlugs\n"
        "    skip: $skip\n"
        "    first: $first\n"
        "  ) {\n"
        "    totalNum\n"
        "    edges {\n"
        "      node {\n"
        "        title\n"
        "        summary\n"
        "        createdAt\n"
        "        topicId\n"
        "        topic { id topLevelCommentCount }\n"
        "        reactions { count reactionType }\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "}"
    ),
    "variables": {
        "orderBy": "MOST_RECENT",
        "keywords": [""],
        "tagSlugs": ["compensation"],
        "skip": 0,
        "first": 3,
    },
}

DETAIL_QUERY = {
    "operationName": "discussPostDetail",
    "query": (
        "query discussPostDetail($topicId: ID!) {\n"
        "  ugcArticleDiscussionArticle(topicId: $topicId) {\n"
        "    title\n"
        "    content\n"
        "    createdAt\n"
        "    topicId\n"
        "  }\n"
        "}"
    ),
    "variables": {"topicId": ""},
}


def main():
    client = httpx.Client(timeout=30.0, headers=HEADERS)
    resp = client.post("https://leetcode.com/graphql", json=LIST_QUERY)
    print("list status:", resp.status_code)
    data = resp.json()
    if "errors" in data:
        print(json.dumps(data["errors"], indent=2))
        return

    articles = data["data"]["ugcArticleDiscussionArticles"]
    print("total:", articles["totalNum"])
    nodes = [e["node"] for e in articles["edges"]]
    print(json.dumps(nodes, indent=2)[:2000])

    topic_id = nodes[0]["topic"]["id"]
    detail = {**DETAIL_QUERY, "variables": {"topicId": topic_id}}
    resp2 = client.post("https://leetcode.com/graphql", json=detail)
    post = resp2.json()["data"]["ugcArticleDiscussionArticle"]
    print("\n--- sample post ---")
    print("title:", post["title"])
    print("content preview:", (post.get("content") or "")[:800])


if __name__ == "__main__":
    main()
