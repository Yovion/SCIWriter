#source("http://bioconductor.org/biocLite.R")   #source("https://bioconductor.org/biocLite.R")
#biocLite("edgeR")

foldChange=1
padj=0.05

# setwd("F:\\CSX\\Gastric_new\\clusterDEGs")          #???ù???Ŀ¼
library("edgeR")
rt=read.table("mRNA.txt",sep="\t",header=T,check.names=F)   #?ĳ??Լ????ļ???
clinical <- data.frame(id = colnames(rt)[-1])
clinical$risk <- ifelse(substr(clinical$id,start = 14,stop = 14) == "0","tumor","normal")

a <- as.data.frame(t(rt[1,-1]))

rt <- rt[-1,]
rt=as.matrix(rt)
rownames(rt)=rt[,1]
exp=rt[,2:ncol(rt)]
dimnames=list(rownames(exp),colnames(exp))
data=matrix(as.numeric(as.matrix(exp)),nrow=nrow(exp),dimnames=dimnames)
data=avereps(data)
data=data[rowMeans(data)>1,]

#group=c("normal","tumor","tumor","normal","tumor")
group=c(rep("normal",12),rep("tumor",116))                         #???հ?֢????????Ʒ??Ŀ?޸?
design <- model.matrix(~group)
y <- DGEList(counts=data,group=group)
y <- calcNormFactors(y)
y <- estimateCommonDisp(y)
y <- estimateTagwiseDisp(y)
et <- exactTest(y,pair = c("normal","tumor"))
topTags(et)
ordered_tags <- topTags(et, n=100000)

allDiff=ordered_tags$table
allDiff=allDiff[is.na(allDiff$FDR)==FALSE,]
diff=allDiff
newData=y$pseudo.counts

# write.table(diff,file="edgerOut.xls",sep="\t",quote=F)
diffSig = diff[(diff$FDR < padj & (diff$logFC>foldChange | diff$logFC<(-foldChange))),]
write.table(diffSig, file="diffSig.xls",sep="\t",quote=F)
