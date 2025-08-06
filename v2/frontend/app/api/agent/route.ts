import { StreamingTextResponse, LangChainStream } from "ai";
import { ChatOpenAI } from "@langchain/openai";
import { ChatPromptTemplate } from "@langchain/core/prompts";
import { AgentExecutor, createOpenAIFunctionsAgent } from "langchain/agents";
import { TavilySearchResults } from "@langchain/community/tools/tavily_search";

export const runtime = "edge";

export async function POST(req: Request) {
    const { stream, handlers } = LangChainStream();
    const body = await req.json();
    const token = req.headers.get("Authorization")?.replace("Bearer ", "");

    if (!token) {
        return new Response("Unauthorized", { status: 401 });
    }

    const llm = new ChatOpenAI({
        modelName: "gpt-4-turbo-preview",
        temperature: 0,
        streaming: true,
    });

    const tools = [new TavilySearchResults({ maxResults: 1 })];

    const prompt = ChatPromptTemplate.fromMessages([
        ["system", "You are a helpful assistant"],
        ["human", "{input}"],
        ["placeholder", "{agent_scratchpad}"],
    ]);

    const agent = await createOpenAIFunctionsAgent({
        llm,
        tools,
        prompt,
    });

    const agentExecutor = new AgentExecutor({
        agent,
        tools,
        verbose: true,
    });

    agentExecutor.invoke({ input: body.message, stream }, { callbacks: [handlers] });

    return new StreamingTextResponse(stream);
}